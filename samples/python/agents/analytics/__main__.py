"""This file serves as the main entry point for the application.

It initializes the A2A server, defines the agent's capabilities,
and starts the server to handle incoming requests. Notice the agent runs on port 10011.
"""

import logging

import click

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from agent import ChartGenerationAgent
from agent_executor import ChartGenerationAgentExecutor
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10011)
def main(host, port):
    """Entry point for the A2A Chart Generation Agent."""
    try:
        capabilities = AgentCapabilities(streaming=False)
        skill = AgentSkill(
            id='chart_generator',
            name='Chart Generator',
            description='Generate a chart based on CSV-like data passed in',
            tags=['generate image', 'edit image'],
            examples=[
                'Generate a chart of revenue: Jan,$1000 Feb,$2000 Mar,$1500'
            ],
        )

        agent_card = AgentCard(
            name='Chart Generator Agent',
            description='Generate charts from structured CSV-like data input.',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=ChartGenerationAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=ChartGenerationAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        request_handler = DefaultRequestHandler(
            agent_executor=ChartGenerationAgentExecutor(),
            task_store=InMemoryTaskStore(),
        )

        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        import uvicorn

        uvicorn.run(server.build(), host=host, port=port)

    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        exit(1)


if __name__ == '__main__':
    main()
