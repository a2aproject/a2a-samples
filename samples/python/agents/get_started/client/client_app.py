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
import httpx
import time
import uuid

from a2a import types
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.utils.message import get_message_text
from a2a.client.helpers import create_text_message_object

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


def sprint(text: str):
    """Print a text with a delay to simulate a long process"""
    time.sleep(0.2)
    print(text)


async def show_agent_card():
    """Show the agent card in the terminal"""
    print("#" * 45)
    agent_card = await get_agent_card()
    sprint(f"Agent Card - Name: {agent_card.name}")
    sprint(f"Agent Card - Capabilities: {agent_card.capabilities}")
    sprint(f"Agent Card - Description: {agent_card.description}")
    sprint(f"Agent Card - Skills: ")
    for i, each in enumerate(agent_card.skills):
        sprint(f"Agent Card - Skills[{i + 1}]:")
        sprint(f"\t Skill - Id: {each.id}")
        sprint(f"\t Skill - Name: {each.name}")
        sprint(f"\t Skill - Description: {each.description}")
        sprint(f"\t Skill - Examples: {each.examples}")
    print("#" * 45)


async def send_message(text_query: str):
    print("########################################")
    print("#### Weather Reporting Poet via A2A ####")
    print("########################################")
    agent_card = await get_agent_card()
    client_factory = ClientFactory(config=ClientConfig(streaming=False))
    client = client_factory.create(agent_card)

    print("To exit use `exit` or `quit`.")
    print(f"user> {text_query}")
    while text_query not in ["exit", "quit"]:
        if text_query:
            # create a client message object
            parts = [types.Part(text=text_query)]
            message = types.Message(
                role=types.Role.ROLE_USER,
                parts=parts,
                message_id=str(uuid.uuid4()),  # Unique ID
            )
            request = types.SendMessageRequest(message=message)
            # Alternatively, you can do the following to create a request object:
            # from a2a.client.helpers import create_text_message_object
            # request = types.SendMessageRequest(message=create_text_message_object(content=query))

            # Sending a message to the server & listening for responses
            response = client.send_message(request=request)
            async for response_chunk, task in response:
                text_response = get_message_text(task.artifacts[0])
                print(f"model> {text_response}")
        text_query = input("user> ").strip()
    print("#" * 45)


if __name__ == "__main__":
    # Ensure the event loop is properly managed
    try:
        asyncio.run(show_agent_card())
        asyncio.run(send_message("How is the Weather in Poland, Warsaw?"))
        # asyncio.run(WeatherClient().run_interactive_terminal())
    except KeyboardInterrupt:
        print("Exiting client due to user interruption.")
