# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module defining a simple A2A client to interact with the Weather Poet server."""

import asyncio

import httpx

from a2a import types
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import (
    display_agent_card,
    get_stream_response_text,
    new_text_message,
)


# The server is assumed to be running locally on port 9999
SERVER_URL = 'http://localhost:9999/'


async def get_agent_card() -> types.AgentCard:
    """Fetches the agent card from the A2A Server.

    Returns:
        types.AgentCard: The fetched agent card.
    """
    async with httpx.AsyncClient() as httpx_client:
        # Initialize the resolver with the server's base URL
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=SERVER_URL,
        )
        return await resolver.get_agent_card()


async def show_agent_card() -> None:
    """Fetches and displays the agent card in the terminal."""
    agent_card = await get_agent_card()
    display_agent_card(agent_card)


async def start_interactive_chat(text_query: str) -> None:
    """Starts an interactive session with the A2A server using a text query.

    Args:
        text_query: The initial query to send to the server.
    """
    print('########################################')
    print('#### Weather Reporting Poet via A2A ####')
    print('########################################')
    # Fetch the agent card to understand capabilities
    agent_card = await get_agent_card()
    # Configure the client (streaming disabled for simpler terminal output)
    client_config = ClientConfig(streaming=False)
    client = await create_client(agent=agent_card, client_config=client_config)

    print('To exit use `exit` or `quit`.')
    print(f'User> {text_query}')
    # Interactive loop for user interaction
    while text_query not in ['exit', 'quit']:
        if text_query:
            # Construct a new user message
            message = new_text_message(
                text=text_query, role=types.Role.ROLE_USER
            )
            request = types.SendMessageRequest(message=message)

            # Send the message to the server and iterate over response chunks
            async for response_chunk in client.send_message(request=request):
                text = get_stream_response_text(response_chunk)
                print(f'Model> {text}\n---')
        # Read the next query from the user
        text_query = await asyncio.to_thread(input, 'User> ')
    print('#' * 45)


if __name__ == '__main__':
    try:
        # Display agent capabilities first
        asyncio.run(show_agent_card())
        # Start the interactive chat with a default query
        asyncio.run(
            start_interactive_chat('How is the Weather in Poland, Warsaw?')
        )
    except KeyboardInterrupt:
        print('\nExiting client due to user interruption.')
