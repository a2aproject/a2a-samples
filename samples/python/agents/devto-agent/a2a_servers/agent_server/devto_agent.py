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
    AGENT_NAME = "Devto_Agent"
    AGENT_DESCRIPTION = "An agent to interact with Devto articles and blogs."
    PORT = 11000
    HOST = "localhost"
    AGENT_URL = f"http://{HOST}:{PORT}/"
    AGENT_VERSION = "0.1.0"
    MODEL = "gemini-2.0-flash"  # Replace with your desired model
    AGENT_SKILLS = [
        AgentSkill(
            id="SKILL_DEVTO_CONTENT",
            name="DevTo Markdown Content",
            description="Generate markdown content for DevTo articles.",
        ),
        AgentSkill(
            id="SKILL_DEVTO_ARTICLES",
            name="DevTo Articles",
            description="Fetch articles from DevTo with or without tags.",
        ),
        AgentSkill(
            id="SKILL_DEVTO_USER_INFO",
            name="DevTo User Info",
            description="Fetch user information from DevTo.",
        ),
        AgentSkill(
            id="SKILL_POST_DEVTO_ARTICLE",
            name="Post DevTo Article",
            description="Create and post article on Devto.",
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

    devto_tools, devto_exit_stack = await get_devto_tools()

    devto_blogs_agent = ADKAgent(
        model=MODEL,
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        tools=devto_tools,
        instructions=(
            "You can retrieve information about DevTo articles, user profiles, and even post articles. "
            "If user asks for markdown content, generate it for specified topic and add relevant tags. "
            "If user asks for articles, you can fetch them by tags or without tags. "
            "If user asks for user profile, you can fetch it by username. "
            "If user asks to post an article, you need to first ask for the topic, then draft markdown content along with images and text. Add relevant tags and post it on DevTo. "
            "Always respond with the result of your action, and if you are unable to perform an action, explain why. "
            "If you need to ask for more information, do so in a clear and concise manner. "
            "If you are unable to perform an action, explain why. "
            "Say 'I'm sorry, I cannot perform that action.' if you are unable to perform an action. "
        )
    )

    task_manager = generate_agent_task_manager(devto_blogs_agent)
    server = A2AServer(
        host=HOST,
        port=PORT,
        endpoint="/devto-agent",
        agent_card=AGENT_CARD,
        task_manager=task_manager,
    )
    print(colored(f"Starting {AGENT_NAME} A2A Server on {AGENT_URL}", "yellow"))
    await server.astart()


if __name__ == "__main__":
    dotenv.load_dotenv()
    asyncio.run(run_agent())