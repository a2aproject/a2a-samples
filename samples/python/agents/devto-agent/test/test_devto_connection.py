# Import libraries
import asyncio
import dotenv
from termcolor import colored
from google.adk import Runner
from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from connector.tools.devto_tools import get_devto_tools

async def get_tools() -> list:
    """
    Retrieves tools from Devto MCP server.
    
    Returns:
        list: A list of tools retrieved from the Devto MCP server.
    """
    tools, exit_stack = await get_devto_tools()
    return tools, exit_stack


async def get_agent():
    """
    Create an agent with Devto tools.
    """

    tools, exit_stack = await get_tools()
    print(f"Retrieved {len(tools)} tools from Devto MCP server.")

    agent = LlmAgent(
        model='gemini-2.0-flash', # Replace with your desired model
        name='DevtoAgent',
        description='An agent to interact with Devto articles and blogs.',
        instruction="You are an agent that can fetch articles, user information, and perform actions related to Devto blogs. Use the tools provided to answer user queries.",
        tools=tools,
    )

    return agent, exit_stack


async def main():
    session_service = InMemorySessionService()
    artifacts_service = InMemoryArtifactService()
    
    print("Creating session...")
    session = session_service.create_session(
        state={},
        app_name='Devto_Agent_App',
        user_id='devto_user',
        session_id='devto_session',
    )

    query = "Fetch the latest articles from Devto."
    print(f"\nQuery: {query}")
    content = types.Content(role='user', parts=[types.Part(text=query)])
    agent, exit_stack = await get_agent()

    print(colored("Agent created successfully.", "green"))
    runner = Runner(
        app_name='Devto_Agent_App',
        session_service=session_service,
        artifact_service=artifacts_service,
        agent=agent,
    )

    event_async = runner.run_async(session_id=session.id, user_id=session.user_id, new_message=content)

    print("********************* Agent Response *********************")
    async for event in event_async:
        if event.is_final_response():
            print(event.content.parts[0].text)

    await exit_stack.aclose()


if __name__ == "__main__":
    dotenv.load_dotenv()
    asyncio.run(main())