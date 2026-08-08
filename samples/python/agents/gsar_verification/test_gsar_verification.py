# ruff: noqa: S101 -- assert is how pytest asserts; same repo convention as
# extensions/timestamp/test_client.py.
"""Real end-to-end smoke test, same shape as helloworld's own test_client.py.

Starts the real agent server as a real subprocess (not imported/mocked),
sends real A2A messages to it, and GSAR-verifies the real response --
across all four reservations in the dataset, in both modes. Skipped
without a live OPENAI_API_KEY, since it makes real, billed API calls --
same convention this sample's own README already states.

Uses `asyncio.run()` from plain sync test functions, matching helloworld's
own pattern -- this repo doesn't depend on pytest-asyncio anywhere else.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time

from pathlib import Path

import pytest

from agent_executor import _DB
from host_verify import build_evidence_corpus, call_remote_agent
from tulip.models.native.openai import OpenAIModel
from tulip.reasoning.gsar_judge import StructuredOutputGSARJudge


PORT = 9876
BASE_URL = f'http://127.0.0.1:{PORT}'
_GROUNDED_SCORE_FLOOR = 0.8

pytestmark = pytest.mark.skipif(
    not os.environ.get('OPENAI_API_KEY'),
    reason='needs a live OPENAI_API_KEY -- makes real, billed API calls',
)


def _start_server(mode: str) -> subprocess.Popen:
    server_path = Path(__file__).parent / '__main__.py'
    env = {**os.environ, 'REMOTE_AGENT_MODE': mode}
    process = subprocess.Popen(  # noqa: S603
        [sys.executable, str(server_path), str(PORT)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(1.5)
    return process


def _judge() -> StructuredOutputGSARJudge:
    return StructuredOutputGSARJudge(
        model=OpenAIModel(model='gpt-4o-mini', api_key=os.environ['OPENAI_API_KEY']),
        strict=True,
    )


async def _verify(reservation_id: str) -> tuple[float, str, list, list]:
    final_message, artifacts = await call_remote_agent(BASE_URL, reservation_id)
    evidence = build_evidence_corpus(artifacts)
    verdict = await _judge().judge(report_synthesis=final_message, evidence_corpus=evidence)
    return (
        verdict.grounding_score,
        verdict.decision_status,
        verdict.contradicted_claims,
        verdict.ungrounded_claims,
    )


@pytest.mark.parametrize('reservation_id', sorted(_DB.keys()))
def test_honest_summary_scores_grounded(reservation_id: str) -> None:
    """Every reservation in the dataset, honestly reported, scores fully grounded."""
    process = _start_server('honest')
    try:
        score, decision, _contradicted, _ungrounded = asyncio.run(_verify(reservation_id))
        assert score >= _GROUNDED_SCORE_FLOOR, (
            f'{reservation_id}: expected grounded, got score={score} decision={decision}'
        )
    finally:
        process.terminate()
        process.wait()


@pytest.mark.parametrize('reservation_id', sorted(_DB.keys()))
def test_hallucinated_summary_flags_the_fabricated_claim(reservation_id: str) -> None:
    """Every reservation, misreporting a different field, gets that claim flagged.

    Same real lookup, same real artifact as the honest case -- only the
    summary differs, per reservation, in what gets fabricated (see
    agent_executor._HALLUCINATED_FIELD).

    Asserting on `contradicted_claims`/`ungrounded_claims` rather than a
    fixed score threshold -- found by testing, not assumed: a summary that
    gets three of four facts right and fabricates one (QRX88B's wrong
    destination) correctly scores in the 0.7s, not near zero, because most
    of the sentence genuinely is grounded. GSAR reporting a proportionate
    score there is correct behavior, not a bug; a rigid `score < 0.8` cutoff
    was the actual bug, caught precisely because this dataset has more than
    one case to disagree with a hardcoded threshold.
    """
    process = _start_server('hallucinating')
    try:
        score, decision, contradicted, ungrounded = asyncio.run(_verify(reservation_id))
        assert contradicted or ungrounded, (
            f'{reservation_id}: expected the fabricated claim to be flagged, '
            f'got score={score} decision={decision}, nothing flagged'
        )
        assert score < 1.0, (
            f'{reservation_id}: a fabrication scoring a perfect 1.0 would be a real miss'
        )
    finally:
        process.terminate()
        process.wait()
