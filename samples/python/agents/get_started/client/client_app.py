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

import asyncio
import time

import httpx

from a2a import types
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import (
    display_agent_card,
    get_stream_response_text,
    new_text_message,
)


# Assuming the server is running at http://localhost:9999 and exposes an /invoke endpoint
SERVER_URL = 'http://localhost:9999/'


async def get_agent_card() -> types.AgentCard:
    """Get the agent card from A2A Server"""
    async with httpx.AsyncClient() as httpx_client:
        # Initialize A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=SERVER_URL,
        )
        agent_card = await resolver.get_agent_card()

    return agent_card


def sprint(text: str):
    """Print a text with a delay to simulate a long process"""
    time.sleep(0.2)
    print(text)


async def show_agent_card():
    """Show the agent card in the terminal"""
    agent_card = await get_agent_card()
    display_agent_card(agent_card)


async def send_message(text_query: str):
    print('########################################')
    print('#### Weather Reporting Poet via A2A ####')
    print('########################################')
    agent_card = await get_agent_card()
    client_config = ClientConfig(streaming=False)
    client = await create_client(agent=agent_card, client_config=client_config)

    print('To exit use `exit` or `quit`.')
    print(f'User> {text_query}')
    while text_query not in ['exit', 'quit']:
        if text_query:
            message = new_text_message(
                text=text_query, role=types.Role.ROLE_USER
            )
            request = types.SendMessageRequest(message=message)

            # Sending a message to the server & listening for responses
            async for response_chunk in client.send_message(request=request):
                text = get_stream_response_text(response_chunk)
                import pdb

                pdb.set_trace()
                print(f'Model> {text}\n---')
        text_query = await asyncio.to_thread(input, 'User> ')
    print('#' * 45)


if __name__ == '__main__':
    # Ensure the event loop is properly managed
    try:
        asyncio.run(show_agent_card())
        asyncio.run(send_message('How is the Weather in Poland, Warsaw?'))
        # asyncio.run(WeatherClient().run_interactive_terminal())
    except KeyboardInterrupt:
        print('Exiting client due to user interruption.')
