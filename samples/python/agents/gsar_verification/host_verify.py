"""A2A host that verifies a remote peer's response against the real
evidence that same peer's own task returned -- using tulip-agents' GSAR
judge (arXiv:2604.23366), a real pip dependency of this sample.

A2A gives every completed Task a final Message (the peer's natural-language
answer) alongside its Artifacts (the peer's actual structured output). GSAR
partitions the message's claims and checks each against the artifacts as
evidence -- catching a remote peer that calls the right skill, gets the
right data back, and still misreports it in its own summary. Tau2-bench
showed this exact gap inside one process; here it's the same check across
a real network boundary between two independent A2A agents.

Nothing here gates or blocks the peer -- this is a host deciding whether to
trust what a peer told it, which is a different, complementary problem from
admission control.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import new_text_message
from a2a.types import Role, SendMessageRequest

from tulip.models.native.openai import OpenAIModel
from tulip.reasoning.gsar_judge import StructuredOutputGSARJudge


async def call_remote_agent(base_url: str, reservation_id: str) -> tuple[str, dict[str, str]]:
    """Sends a real A2A message, returns (final_message_text, {artifact_name: text})."""
    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        agent_card = await resolver.get_agent_card()

        client = await create_client(agent=agent_card, client_config=ClientConfig(streaming=False))
        message = new_text_message(reservation_id, role=Role.ROLE_USER)
        request = SendMessageRequest(message=message)

        final_message = ""
        artifacts: dict[str, str] = {}
        async for event in client.send_message(request):
            task = getattr(event, "task", None) or event
            status_message = getattr(getattr(task, "status", None), "message", None)
            if status_message is not None:
                for part in getattr(status_message, "parts", []) or []:
                    text = getattr(part, "text", None) or getattr(getattr(part, "root", None), "text", None)
                    if text:
                        final_message = text
            for artifact in getattr(task, "artifacts", []) or []:
                name = getattr(artifact, "name", None) or "artifact"
                for part in getattr(artifact, "parts", []) or []:
                    text = getattr(part, "text", None) or getattr(getattr(part, "root", None), "text", None)
                    if text:
                        artifacts[name] = text

        await client.close()
        return final_message, artifacts


def build_evidence_corpus(artifacts: dict[str, str]) -> str:
    """Renders the peer's own returned artifacts as the evidence GSAR
    scores its final message against."""
    lines = []
    for name, text in artifacts.items():
        lines.append(f"Artifact {name!r}: {text}")
    return "\n".join(lines) if lines else "No artifacts were returned."


async def main() -> None:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:9999"
    reservation_id = sys.argv[2] if len(sys.argv) > 2 else "ZFA04Y"

    print(f"Sending real A2A message to {base_url}: {reservation_id!r}")
    final_message, artifacts = await call_remote_agent(base_url, reservation_id)

    print(f"\nPeer's final message: {final_message!r}")
    print(f"Peer's real artifacts: {json.dumps(artifacts, indent=2)}")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("\nOPENAI_API_KEY not set -- skipping the live GSAR judge call.")
        return

    judge = StructuredOutputGSARJudge(model=OpenAIModel(model="gpt-4o-mini", api_key=api_key), strict=True)
    evidence = build_evidence_corpus(artifacts)
    verdict = await judge.judge(report_synthesis=final_message, evidence_corpus=evidence)

    print(f"\nGSAR verdict: grounding_score={verdict.grounding_score:.2f} decision={verdict.decision_status}")
    if verdict.decision_status == "abstain":
        print(f"  abstain_reason: {verdict.abstain_reason}")
    if verdict.contradicted_claims:
        print(f"  contradicted: {[c.text for c in verdict.contradicted_claims]}")
    if verdict.ungrounded_claims:
        print(f"  ungrounded: {[c.text for c in verdict.ungrounded_claims]}")


if __name__ == "__main__":
    asyncio.run(main())
