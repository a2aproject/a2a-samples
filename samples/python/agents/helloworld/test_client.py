import asyncio
import subprocess
import sys
import time

from pathlib import Path

import pytest

from a2a.client import ClientConfig, create_client
from a2a.helpers import new_text_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest


@pytest.fixture(scope='session', autouse=True)
def start_server():
    server_path = Path(__file__).parent / '__main__.py'
    process = subprocess.Popen(  # noqa: S603
        [sys.executable, str(server_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait a moment for the server to start
    time.sleep(1.5)

    yield

    process.terminate()
    process.wait()


async def get_agent_card():
    print('Initializes the A2ACardResolver instance with an HTTP client')
    # --8<-- [start:A2ACardResolver]
    import httpx  # noqa: PLC0415

    from a2a.client import A2ACardResolver  # noqa: PLC0415

    # Initializes the A2ACardResolver instance with an HTTP client, base URL,
    # and uses the default path for the agent card.
    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url='http://127.0.0.1:9999',
            # Provide agent_card_path, if your agent uses a different path
            # agent_card_path=''  # noqa: ERA001
        )
        public_agent_card = await resolver.get_agent_card()
        # --8<-- [end:A2ACardResolver]
        print('\nSuccessfully fetched the public agent card:')
    return public_agent_card


async def show_agent_card():
    from a2a.helpers import display_agent_card  # noqa: PLC0415

    public_agent_card = await get_agent_card()
    display_agent_card(public_agent_card)


async def send_message(text_query: str = 'Hi there'):
    public_agent_card = await get_agent_card()
    print('\n--- Public Agent Card - Non-Streaming Call ---')
    # --8<-- [start:message_send]
    from a2a.client import ClientConfig, create_client  # noqa: PLC0415
    from a2a.helpers import new_text_message  # noqa: PLC0415
    from a2a.types.a2a_pb2 import Role, SendMessageRequest  # noqa: PLC0415

    print('\nInitializing a non-streaming client.')
    config = ClientConfig(streaming=False)
    client = await create_client(agent=public_agent_card, client_config=config)

    # Creates a new text message to be sent to the A2A Server.
    # Ex: text_query = 'Why is the sky blue?'  # noqa: ERA001
    message = new_text_message(text_query, role=Role.ROLE_USER)
    request = SendMessageRequest(message=message)

    print('Response:')
    async for chunk in client.send_message(request):
        print(chunk)
    # --8<-- [end:message_send]
    await client.close()


async def send_steaming_message(text_query: str = 'Hi there'):
    public_agent_card = await get_agent_card()

    # Creates a new text message to be sent to the A2A Server.
    # Ex: text_query = 'Why is the sky blue?'  # noqa: ERA001
    message = new_text_message(text_query, role=Role.ROLE_USER)
    request = SendMessageRequest(message=message)

    print('\n--- Public Agent Card - Streaming Call ---')
    # --8<-- [start:message_stream]
    print('\nInitializing a streaming client.')
    client_config = ClientConfig(streaming=True)  # Streaming
    client = await create_client(agent=public_agent_card, client_config=client_config)

    print('Response:')
    async for chunk in client.send_message(request):
        print(chunk)
    # --8<-- [end:message_stream]
    await client.close()


async def show_extended_card():
    from a2a.helpers import display_agent_card  # noqa: PLC0415
    from a2a.types.a2a_pb2 import GetExtendedAgentCardRequest  # noqa: PLC0415

    public_agent_card = await get_agent_card()
    config = ClientConfig(streaming=False)
    client = await create_client(agent=public_agent_card, client_config=config)

    print('\n--- Extended Agent Card - Non-Streaming Call ---')
    extended_card = await client.get_extended_agent_card(GetExtendedAgentCardRequest())
    print('\nSuccessfully fetched the authenticated extended agent card:')
    display_agent_card(extended_card)
    await client.close()


def test_client_workflow(text_query: str = 'Hi there!'):
    """
    This test function is intended to be used to test the client workflow
    for multiple queries
    """
    asyncio.run(show_agent_card())
    asyncio.run(send_message(text_query))
    asyncio.run(send_steaming_message(text_query))
    asyncio.run(show_extended_card())


def main():
    print('\nStarting an internactive session with A2A Server [http://127.0.0.1:9999]')
    print('Use `exit` to quit.')
    prompt = input('user > ')
    while prompt and prompt != 'exit':
        asyncio.run(send_message(prompt))
        prompt = input('--\nuser > ')


if __name__ == '__main__':
    main()
