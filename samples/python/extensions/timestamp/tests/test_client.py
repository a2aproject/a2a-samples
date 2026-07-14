# ruff: noqa: S101
import datetime
import os
import subprocess
import sys
import time

from pathlib import Path

import httpx
import pytest

from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import (
    Message,
    Part,
    Role,
    SendMessageRequest,
    TaskState,
)
from client import wrap_client_factory
from core import TIMESTAMP_FIELD, TimestampExtension


_AGENT_URL = 'http://127.0.0.1:9998'
_FIXED_TS = 1_700_000_000.0


@pytest.fixture(scope='session', autouse=True)
def start_server():
    server_path = Path(__file__).parent / '__main__.py'
    env = os.environ.copy()
    env['TIMESTAMP_EXT_FIXED_CLOCK'] = str(_FIXED_TS)
    process = subprocess.Popen(  # noqa: S603
        [sys.executable, str(server_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    # Wait a moment for the server to start
    time.sleep(1.5)

    yield

    process.terminate()
    process.wait()


@pytest.mark.asyncio
async def test_timestamp_extension_round_trip():
    expected_iso = datetime.datetime.fromtimestamp(_FIXED_TS, datetime.timezone.utc).isoformat()
    ext = TimestampExtension(now_fn=lambda: _FIXED_TS)

    async with httpx.AsyncClient(base_url=_AGENT_URL) as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=_AGENT_URL)
        card = await resolver.get_agent_card()

        factory = wrap_client_factory(
            factory=ClientFactory(config=ClientConfig(httpx_client=httpx_client, streaming=True)),
            ext=ext,
        )
        client = factory.create(card=card)

        request = SendMessageRequest(
            message=Message(
                role=Role.ROLE_USER,
                parts=[Part(text='hi')],
                message_id='req-1',
            )
        )

        print('\n--- streaming response from the agent ---')
        artifacts = []
        status_messages = []
        async for chunk in client.send_message(request=request):
            match chunk.WhichOneof('payload'):
                case 'artifact_update':
                    art = chunk.artifact_update.artifact
                    artifacts.append(art)
                    print(f'  artifact "{art.name}" @ {art.metadata[TIMESTAMP_FIELD]}')
                case 'status_update':
                    status = chunk.status_update.status
                    if status.HasField('message'):
                        status_messages.append(status.message)
                        print(
                            f'  status={TaskState.Name(status.state)} message '
                            f'@ {status.message.metadata[TIMESTAMP_FIELD]}'
                        )
                    else:
                        print(f'  status={TaskState.Name(status.state)}')
                case kind:
                    print(f'  event of kind {kind}')

        await client.close()

    assert artifacts, 'agent did not emit an artifact'
    assert status_messages, 'agent did not emit a status message'
    for art in artifacts:
        assert art.metadata[TIMESTAMP_FIELD] == expected_iso
    for msg in status_messages:
        assert msg.metadata[TIMESTAMP_FIELD] == expected_iso


async def run_client(text_query: str = 'hi'):
    ext = TimestampExtension()
    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=_AGENT_URL)
        card = await resolver.get_agent_card()

        factory = wrap_client_factory(
            factory=ClientFactory(config=ClientConfig(httpx_client=httpx_client, streaming=True)),
            ext=ext,
        )
        client = factory.create(card=card)

        request = SendMessageRequest(
            message=Message(
                role=Role.ROLE_USER,
                parts=[Part(text=text_query)],
                message_id='req-1',
            )
        )

        print(f'\nSending: "{text_query}"')
        async for chunk in client.send_message(request=request):
            match chunk.WhichOneof('payload'):
                case 'artifact_update':
                    art = chunk.artifact_update.artifact
                    ts = art.metadata[TIMESTAMP_FIELD] if TIMESTAMP_FIELD in art.metadata else 'no timestamp'
                    print(f'  artifact "{art.name}" @ {ts}')
                case 'status_update':
                    status = chunk.status_update.status
                    if status.HasField('message'):
                        ts = status.message.metadata[TIMESTAMP_FIELD] if TIMESTAMP_FIELD in status.message.metadata else 'no timestamp'
                        print(
                            f'  status={TaskState.Name(status.state)} message '
                            f'@ {ts}'
                        )
                    else:
                        print(f'  status={TaskState.Name(status.state)}')
                case kind:
                    print(f'  event of kind {kind}')

        await client.close()


def main():
    import asyncio
    print(f'\nStarting interactive session with Timestamp Agent Server [{_AGENT_URL}]')
    print('Use `exit` to quit.')
    prompt = input('user > ')
    while prompt and prompt != 'exit':
        asyncio.run(run_client(prompt))
        prompt = input('--\nuser > ')


if __name__ == '__main__':
    main()
