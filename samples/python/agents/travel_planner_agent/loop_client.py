import asyncio

from typing import Any
from uuid import uuid4

import httpx

from a2a.client import (
    A2ACardResolver,
    ClientConfig,
    ClientFactory,
    Client,
    create_text_message_object
)
from a2a.types import (
    TransportProtocol,
    Task
)


def print_welcome_message() -> None:
    print('Welcome to the generic A2A client!')
    print("Please enter your query (type 'exit' to quit):")


def get_user_query() -> str:
    return input('\n> ')


async def interact_with_server(client: Client) -> None:
    while True:
        user_input = get_user_query()
        if user_input.lower() == 'exit':
            print('bye!~')
            break

        try:
            # Create the message object
            request = create_text_message_object(content=user_input)

            # Send the request and get the streaming messages
            async for response in client.send_message(request):
                task, _ = response
                print(get_response_text(task))
        except Exception as e:
            print(f'An error occurred: {e}')


def get_response_text(task: Task) -> str:
    return task.artifacts[-1].parts[0].root.text


async def main() -> None:
    print_welcome_message()
    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url="http://localhost:10001",
            # agent_card_path uses default, extended_agent_card_path also uses default
        )
        agent_card = await resolver.get_agent_card()

        # Create A2A client with the agent card
        config = ClientConfig(
            httpx_client=httpx_client,
            supported_transports=[
                TransportProtocol.jsonrpc,
                TransportProtocol.http_json,
            ],
            streaming=agent_card.capabilities.streaming,
        )
        client = ClientFactory(config).create(agent_card)

        await interact_with_server(client)


if __name__ == '__main__':
    asyncio.run(main())
