# Import libraries
import asyncio
import sys
import os
import dotenv
from termcolor import colored

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from a2a_servers.common.types import AgentSkill
from a2a_servers.agents.adk_agent import ADKAgent
from a2a_servers.common.server.server import A2AServer
from a2a_servers.agent_server.utils import generate_agent_card, generate_agent_task_manager
from connector.tools.devto_tools import get_devto_tools

async def run_agent():
    AGENT_NAME = "Host_Agent"
    AGENT_DESCRIPTION = "An agent orchestrates the decomposition of the user request into tasks that can be performed by the child agents."
    PORT = 10000
    HOST = "localhost"
    AGENT_URL = f"http://{HOST}:{PORT}/"
    AGENT_VERSION = "0.1.0"
    MODEL = "gemini-2.0-flash"  # Replace with your desired model
    AGENT_SKILLS = [
        AgentSkill(
            id="COORDINATE_AGENT_TASKS",
            name="coordinate_tasks",
            description="coordinate tasks between agents.",
        )
    ]

    AGENT_CARD = generate_agent_card(
        agent_name=AGENT_NAME,
        agent_description=AGENT_DESCRIPTION,
        agent_url=AGENT_URL,
        agent_version=AGENT_VERSION,
        can_stream=False,
        can_push_notifications=False,
        can_state_transition_history=True,
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=AGENT_SKILLS,
    )

    remote_agent_urls = [
        'http://localhost:11000/devto-agent',  # Devto Agent
    ]

    host_agent = ADKAgent(
        model=MODEL,
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        tools=[],
        instructions=(
            "You are a host agent that orchestrates the decomposition of the user request into tasks "
            "that can be performed by the child agents. You will coordinate tasks between agents."
        ),
        is_host_agent=True,
        remote_agent_addresses=remote_agent_urls,
    )

    task_manager = generate_agent_task_manager(host_agent)
    server = A2AServer(
        host=HOST,
        port=PORT,
        endpoint="/host_agent",
        agent_card=AGENT_CARD,
        task_manager=task_manager,
    )
    print(colored(f"Starting {AGENT_NAME} A2A Server on {AGENT_URL}"), "yellow")
    await server.astart()


if __name__ == "__main__":
    dotenv.load_dotenv()
    asyncio.run(run_agent())