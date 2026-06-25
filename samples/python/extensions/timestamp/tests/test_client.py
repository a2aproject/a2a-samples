# ruff: noqa: S101
import datetime
import os
import subprocess
import sys
import time

from pathlib import Path

import httpx
import pytest

from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    Message,
    Part,
    Role,
    SendMessageRequest,
    TaskState,
)
from timestamp_ext.client import wrap_client_factory
from timestamp_ext.core import TIMESTAMP_FIELD, TimestampExtension


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

    # Recreate the card on the client side for discovery
    card = AgentCard(
        name='Echo',
        description='echo agent that demonstrates the timestamp extension',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[
            AgentInterface(
                protocol_binding='JSONRPC',
                url=_AGENT_URL,
                protocol_version='1.0',
            )
        ],
    )
    # Add capabilities to match the server
    ext.add_to_card(card=card)

    async with httpx.AsyncClient(base_url=_AGENT_URL) as httpx_client:
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
            kind = chunk.WhichOneof('payload')
            if chunk.HasField('artifact_update'):
                art = chunk.artifact_update.artifact
                artifacts.append(art)
                print(f'  artifact "{art.name}" @ {art.metadata[TIMESTAMP_FIELD]}')
            elif chunk.HasField('status_update'):
                status = chunk.status_update.status
                if status.HasField('message'):
                    msg = status.message
                    status_messages.append(msg)
                    print(
                        f'  status={TaskState.Name(status.state)} message '
                        f'@ {msg.metadata[TIMESTAMP_FIELD]}'
                    )
                else:
                    print(f'  status={TaskState.Name(status.state)}')
            else:
                print(f'  event of kind {kind}')

        await client.close()

    assert artifacts, 'agent did not emit an artifact'
    assert status_messages, 'agent did not emit a status message'
    for art in artifacts:
        assert art.metadata[TIMESTAMP_FIELD] == expected_iso
    for msg in status_messages:
        assert msg.metadata[TIMESTAMP_FIELD] == expected_iso
