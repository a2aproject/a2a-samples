import logging
import os

import click
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from dotenv import load_dotenv
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from jev_host_executor import create_jev_executor
from traceability_ext import TraceabilityExtension


load_dotenv()

logging.basicConfig()

DEFAULT_HOST = '0.0.0.0'  # noqa: S104 - the sample listens on all interfaces on purpose
DEFAULT_PORT = 8083


def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, router: str = 'llm') -> None:
    """Start the host A2A server.

    ``router`` is ``llm`` (the ADK Gemini agent, the default) or ``jev`` (TypeSafe's Jev picks
    the remote agent and the host forwards the message, with no LLM in the loop).
    """
    # which remote agent to use and forwards the message, with no LLM in the loop.
    if (
        router == 'llm'
        and os.getenv('GOOGLE_GENAI_USE_VERTEXAI') != 'TRUE'
        and not os.getenv('GOOGLE_API_KEY')
    ):
        raise ValueError(
            'GOOGLE_API_KEY environment variable not set and GOOGLE_GENAI_USE_VERTEXAI is not TRUE.'
        )

    skill = AgentSkill(
        id='host_agent_search',
        name='Search host_agent',
        description='Helps with weather in city, or states, and airbnb',
        tags=['host_agent'],
        examples=['weather in LA, CA, and airbnb in LA, CA'],
    )

    app_url = os.environ.get('APP_URL', f'http://{host}:{port}')

    traceability_ext = TraceabilityExtension()
    capabilities = AgentCapabilities(
        streaming=True,
        extensions=[
            traceability_ext.agent_extension(),
        ],
    )

    agent_card = AgentCard(
        name='Host A2A Agent',
        description='A2A server that helps with weather and airbnb',
        url=app_url,
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=capabilities,
        skills=[skill],
    )

    remote_agent_addresses = [
        os.getenv('AIR_AGENT_URL', 'http://localhost:10002'),
        os.getenv('WEA_AGENT_URL', 'http://localhost:10001'),
    ]
    if router == 'jev':
        agent_executor = create_jev_executor(remote_agent_addresses)
    else:
        # Imported here because routing_agent builds the ADK agent on import.
        from host_agent_executor import HostAgentExecutor  # noqa: PLC0415
        from routing_agent import root_agent  # noqa: PLC0415

        runner = Runner(
            app_name=agent_card.name,
            agent=root_agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        agent_executor = HostAgentExecutor(runner, agent_card)

    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, task_store=InMemoryTaskStore()
    )

    a2a_app = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)

    uvicorn.run(a2a_app.build(), host=host, port=port)


@click.command()
@click.option('--host', 'host', default=DEFAULT_HOST)
@click.option('--port', 'port', default=DEFAULT_PORT)
@click.option(
    '--router',
    'router',
    type=click.Choice(['llm', 'jev']),
    default=lambda: os.getenv('HOST_ROUTER', 'llm'),
    show_default='HOST_ROUTER or llm',
)
def cli(host: str, port: int, router: str) -> None:
    """Run the host A2A server."""
    main(host, port, router)


if __name__ == '__main__':
    cli()
