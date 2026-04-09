
import asyncio
import httpx
import json

from a2a import types
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.client.helpers import create_text_message_object
from a2a.utils.message import get_message_text

# Assuming the server is running at http://localhost:9999 and exposes an /invoke endpoint
SERVER_URL = "http://localhost:9999/"

async def get_agent_card():
    """Get the agent card from A2A Server"""
    async with httpx.AsyncClient() as httpx_client:
        # Initialize A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=SERVER_URL,
        )
        agent_card: types.AgentCard = await resolver.get_agent_card()
    return agent_card

import time

def sprint(text: str):
    """Print a text with a delay to simulate a long process"""
    time.sleep(0.2)
    print(text)

async def show_agent_card():
    """Show the agent card in the terminal"""
    print('#' * 45)
    agent_card = await get_agent_card()
    sprint(f'Agent Card - Name: {agent_card.name}')
    sprint(f'Agent Card - Capabilities: {agent_card.capabilities}')
    sprint(f'Agent Card - Description: {agent_card.description}')
    sprint(f'Agent Card - Skills: ')
    for i, each in enumerate(agent_card.skills):
        sprint(f'Agent Card - Skills[{i + 1}]:')
        sprint(f'\t Skill - Id: {each.id}')
        sprint(f'\t Skill - Name: {each.name}')
        sprint(f'\t Skill - Description: {each.description}')
        sprint(f'\t Skill - Examples: {each.examples}')
    print('#' * 45)


async def send_message(query:str):
    print('#' * 45)
    agent_card = await get_agent_card()
    client_factory = ClientFactory(config=ClientConfig(streaming=False))
    client = client_factory.create(agent_card)

    print(f'user> {query}')
    # while query:
    parts = [types.Part(text=query)]
    message = types.Message(
        role=types.Role.ROLE_USER,
        parts=parts,
        message_id="ABCD123456789", # unique id
    )
    request = types.SendMessageRequest(message=message)
    # TODO: use a better way to create_text_message_object
    response = client.send_message(request=request)

    async for response_chunk, task in response:
        text_response = get_message_text(task.artifacts[0])
        print(f'model> {text_response}')
    print('#' * 45)

if __name__ == '__main__':
    # Ensure the event loop is properly managed
    try:
        asyncio.run(show_agent_card())
        asyncio.run(send_message("How is the Weather in Poland, Warsaw?"))
        # asyncio.run(WeatherClient().run_interactive_terminal())
    except KeyboardInterrupt:
        print("Exiting client due to user interruption.")
