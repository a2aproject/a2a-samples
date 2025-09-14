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
from host_agent_executor import (
    HostAgentExecutor,
)
from routing_agent import (
    root_agent,
)
from traceability_ext import TraceabilityExtension


load_dotenv()

logging.basicConfig()

DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 8083


def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    # Verify an API key is set.
    # Not required if using Vertex AI APIs.
    if os.getenv('GOOGLE_GENAI_USE_VERTEXAI') != 'TRUE' and not os.getenv(
        'GOOGLE_API_KEY'
    ):
        raise ValueError(
            'GOOGLE_API_KEY environment variable not set and '
            'GOOGLE_GENAI_USE_VERTEXAI is not TRUE.'
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

    adk_agent = root_agent
    runner = Runner(
        app_name=agent_card.name,
        agent=adk_agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )
    agent_executor = HostAgentExecutor(runner, agent_card)

    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, task_store=InMemoryTaskStore()
    )

    a2a_app = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )

    uvicorn.run(a2a_app.build(), host=host, port=port)


@click.command()
@click.option('--host', 'host', default=DEFAULT_HOST)
@click.option('--port', 'port', default=DEFAULT_PORT)
def cli(host: str, port: int):
    main(host, port)


if __name__ == '__main__':
    cli()
