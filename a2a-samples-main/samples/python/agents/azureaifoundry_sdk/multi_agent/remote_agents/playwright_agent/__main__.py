import logging

import click
import httpx

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, InMemoryPushNotifier
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agent_executor import SemanticKernelMCPAgentExecutor
from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


@click.command()
@click.option('--host', default='localhost')
@click.option('--port', default=10001)
def main(host, port):
    """Starts the Semantic Kernel MCP Agent server using A2A."""
    httpx_client = httpx.AsyncClient()
    request_handler = DefaultRequestHandler(
        agent_executor=SemanticKernelMCPAgentExecutor(),
        task_store=InMemoryTaskStore(),
        push_notifier=InMemoryPushNotifier(httpx_client),
    )

    server = A2AStarletteApplication(
        agent_card=get_agent_card(host, port), http_handler=request_handler
    )
    import uvicorn

    uvicorn.run(server.build(), host=host, port=port)


def get_agent_card(host: str, port: int):
    """Returns the Agent Card for the Semantic Kernel MCP Agent."""

    # Build the agent card
    capabilities = AgentCapabilities(streaming=True)
    skill_mcp_tools = AgentSkill(
        id='playwright_tools',
        name='PlaywrightTools',
        description=(
            'Provides tools to access browser automation capabilities'
            'including navigation, screenshot, and more.'
        ),
        tags=['browser', 'playwright', 'screenshot', 'html', 'navigation'],
        examples=[
            'Navigation to  https://github.com/kinfey',
        ],
    )

    agent_card = AgentCard(
        name='PlaywrightToolsAgent',
        description=(
            'This agent provides playwright automation capabilities'
            'and access browser automation tools'
        ),
        url=f'http://localhost:10001/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=capabilities,
        skills=[skill_mcp_tools],
    )

    return agent_card


if __name__ == '__main__':
    main()
