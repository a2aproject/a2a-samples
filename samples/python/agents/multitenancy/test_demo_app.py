"""test_demo_app.py -- black-box pytest checks for the multi-tenancy demo.

Starts a2a_server.py once, then for each of the three tenant agents sends a
text message and asserts we get some text back. Nothing about reply content.

    pip install "a2a-sdk>=1.0.3" uvicorn starlette httpx pytest
    pytest test_demo_app.py
"""

import asyncio
import subprocess
import sys
import time

from pathlib import Path

import httpx
import pytest

from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import new_text_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest


BASE_URL = 'http://127.0.0.1:9999'


@pytest.fixture(scope='session', autouse=True)
def start_server():
    """Start a2a_server.py once for the whole test session, then tear it down."""
    server_path = Path(__file__).parent / 'a2a_server.py'
    process = subprocess.Popen(  # noqa: S603
        [sys.executable, str(server_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Poll until the server is ready instead of a fixed sleep (avoids races).
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            httpx.get(f'{BASE_URL}/hello/.well-known/agent-card.json', timeout=1.0)
            break
        except httpx.HTTPError:
            time.sleep(0.25)
    else:
        process.terminate()
        raise RuntimeError('a2a_server.py did not become ready in time')

    yield

    process.terminate()
    process.wait()


async def _send(path: str, text: str) -> str:
    """Send `text` to the agent at `path` and return the reply text."""
    async with httpx.AsyncClient() as http:
        resolver = A2ACardResolver(httpx_client=http, base_url=f'{BASE_URL}{path}')
        card = await resolver.get_agent_card()

    client = await create_client(agent=card, client_config=ClientConfig(streaming=False))
    request = SendMessageRequest(message=new_text_message(text, role=Role.ROLE_USER))
    reply = ''
    try:
        async for event in client.send_message(request):
            if event.WhichOneof('payload') == 'task':
                for artifact in event.task.artifacts:
                    for part in artifact.parts:
                        reply += part.text
    finally:
        await client.close()
    return reply


def test_hello_agent():
    assert asyncio.run(_send('/hello', 'hi'))  # noqa: S101


def test_palindrome_agent():
    assert asyncio.run(_send('/palindrome', 'racecar'))  # noqa: S101


def test_reverse_agent():
    assert asyncio.run(_send('/reverse', 'a b c'))  # noqa: S101
