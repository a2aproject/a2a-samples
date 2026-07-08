"""a2a_client.py -- Interactive client for the multi-tenancy demo (a2a_server.py).

Companion to the "A2A Multi-Tenancy" blog post.

    pip install "a2a-sdk>=1.0.3" httpx
    python a2a_server.py          # in one terminal
    python a2a_client.py          # in another (non-streaming, default)
    python a2a_client.py --mode stream   # streaming replies

Flow:
  1. The client discovers the agents the server hosts (one Agent Card each).
  2. It prints a menu -- press 1, 2 or 3 to pick which agent to connect to.
  3. Type a message; the chosen agent replies (hello / palindrome / word-reverse).
  4. Press Enter on an empty message to exit.

The only CLI option is --mode, which selects how replies are received:
  --mode message   non-streaming: one reply per message (default)
  --mode stream    streaming:    events arrive as the agent works
"""

import argparse
import asyncio
import os

from collections.abc import Iterable

import httpx

from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_message_text, new_text_message
from a2a.types import AgentCard
from a2a.types.a2a_pb2 import Artifact, Role, SendMessageRequest, StreamResponse


PORT = int(os.environ.get('A2A_PORT', '9999'))
BASE_URL = f'http://127.0.0.1:{PORT}'

# The sub-paths a2a_server.py exposes, in menu order.
AGENT_PATHS = ['/hello', '/palindrome', '/reverse']


def _print_artifacts(artifacts: Iterable[Artifact]) -> None:
    for artifact in artifacts:
        for part in artifact.parts:
            if part.text:
                print(f'agent > {part.text}')


def print_reply(event: StreamResponse) -> None:
    """Print the human-readable reply from a StreamResponse (either mode)."""
    kind = event.WhichOneof('payload')
    if kind == 'task':  # non-streaming: full task
        _print_artifacts(event.task.artifacts)
    elif kind == 'artifact_update':  # streaming: the result chunk(s)
        _print_artifacts([event.artifact_update.artifact])
    elif kind == 'message':
        print(f'agent > {get_message_text(event.message)}')
    # 'status_update' (working/completed) is progress noise -- ignored here.


async def discover_agents(
    http: httpx.AsyncClient,
) -> list[tuple[str, AgentCard]]:
    """Fetch each agent's card from its own sub-path."""
    found: list[tuple[str, AgentCard]] = []
    for path in AGENT_PATHS:
        # A2ACardResolver reads the Agent Card from <base_url>/.well-known/...
        # Because each tenant has its own sub-path, we resolve one card per path.
        resolver = A2ACardResolver(httpx_client=http, base_url=f'{BASE_URL}{path}')
        try:
            card = await resolver.get_agent_card()
            found.append((path, card))
        except Exception as exc:  # noqa: BLE001 - demo: show why an agent is skipped
            print(f'(skipping {path}: {exc})')
    return found


def choose_agent(
    agents: list[tuple[str, AgentCard]],
) -> tuple[str, AgentCard] | None:
    """Print the menu and return the (path, card) the user picks, or None."""
    print('\nWhich A2A agent do you want to connect to?')
    for i, (path, card) in enumerate(agents, start=1):
        print(f'  {i}. {card.name}  ({BASE_URL}{path}) - {card.description}')
    choice = input('Select 1, 2 or 3 (Enter to quit): ').strip()
    if not choice:
        return None
    try:
        return agents[int(choice) - 1]
    except (ValueError, IndexError):
        print('Invalid choice.')
        return None


# Friendly labels for the Agent Card's protocol binding.
PROTOCOL_LABELS = {
    'JSONRPC': 'JSON-RPC over HTTP',
    'HTTP+JSON': 'HTTP + JSON',
    'GRPC': 'gRPC',
}


def describe_agent(card: AgentCard) -> None:
    """Print a short, friendly summary built from the agent's Agent Card."""
    iface = card.supported_interfaces[0] if card.supported_interfaces else None
    protocol = (
        PROTOCOL_LABELS.get(iface.protocol_binding, iface.protocol_binding) if iface else 'unknown'
    )
    endpoint = iface.url if iface else 'n/a'
    inputs = ', '.join(card.default_input_modes) or 'text'
    outputs = ', '.join(card.default_output_modes) or 'text'
    skills = ', '.join(skill.name for skill in card.skills) or '-'

    print(f"\nYou're connected to the {card.name}.")
    print(f'  {card.description}')
    print('  --- from its Agent Card ---')
    print(f'  - Endpoint : {endpoint}')
    print(f'  - Protocol : {protocol}')
    print(f'  - Format   : {inputs} in -> {outputs} out')
    print(f'  - Skills   : {skills}')


async def main(mode: str) -> None:
    """Discover the agents, let the user pick one, and chat with it."""
    async with httpx.AsyncClient() as http:
        agents = await discover_agents(http)
        if not agents:
            print('No agents reachable. Is a2a_server.py running?')
            return

        picked = choose_agent(agents)
        if not picked:
            print('Bye!')
            return
        _path, card = picked

        # Build a client for the chosen agent. The card carries the endpoint, so
        # the client knows where to send requests; streaming is toggled by --mode.
        client = await create_client(
            agent=card,
            client_config=ClientConfig(streaming=(mode == 'stream')),
        )
        describe_agent(card)
        print('\nType a message (empty to exit).')
        try:
            while True:
                # input() is blocking, so run it off the event loop.
                text = (await asyncio.to_thread(input, 'you   > ')).strip()
                if not text:  # empty message -> exit
                    print('Bye!')
                    break
                # Wrap the user's text in an A2A message and send it. Replies are
                # streamed back as events, which print_reply renders per mode.
                request = SendMessageRequest(message=new_text_message(text, role=Role.ROLE_USER))
                async for event in client.send_message(request):
                    print_reply(event)
        finally:
            # Always close the client to release the underlying HTTP connection.
            await client.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Interactive A2A multi-tenancy client.')
    parser.add_argument(
        '--mode',
        choices=['message', 'stream'],
        default='message',
        help="how replies are received: 'message' (non-streaming, default) or 'stream' (streaming)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.mode))
