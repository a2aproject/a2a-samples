import logging
import os

import click

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agent import RestaurantAgent
from agent_executor import RestaurantAgentExecutor
from dotenv import load_dotenv
from gulfui_ext import GulfUIExtension  # <-- This imports File 1


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


@click.command()
@click.option('--host', default='localhost')
@click.option('--port', default=10002)
def main(host, port):
    try:
        # Check for API key only if Vertex AI is not configured
        if not os.getenv('GOOGLE_GENAI_USE_VERTEXAI') == 'TRUE':
            if not os.getenv('GEMINI_API_KEY'):
                raise MissingAPIKeyError(
                    'GEMINI_API_KEY environment variable not set and GOOGLE_GENAI_USE_VERTEXAI is not TRUE.'
                )

        hello_ext = GulfUIExtension()  # <-- Instantiate our extension
        capabilities = AgentCapabilities(
            streaming=True,
            extensions=[
                hello_ext.agent_extension(),  # This advertises the Gulf UI capability
            ],
        )
        skill = AgentSkill(
            id='find_restaurants',
            name='Find Restaurants Tool',
            description='Helps find restaurants based on user criteria (e.g., cuisine, location).',
            tags=['restaurant', 'finder'],
            examples=['Find me the top 10 chinese restaurants in the US'],
        )
        agent_card = AgentCard(
            name='Restaurant Agent',
            description='This agent helps find restaurants based on user criteria.',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            default_input_modes=RestaurantAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=RestaurantAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )
        agent_executor = (
            RestaurantAgentExecutor()
        )  # The simple, text-only executor

        # This wraps the simple executor in our smart UI wrapper
        agent_executor = hello_ext.wrap_executor(agent_executor)

        request_handler = DefaultRequestHandler(
            agent_executor=agent_executor,  # Pass the wrapped executor to the handler
            task_store=InMemoryTaskStore(),
        )
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )
        import uvicorn

        uvicorn.run(server.build(), host=host, port=port)
    except MissingAPIKeyError as e:
        logger.error(f'Error: {e}')
        exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        exit(1)


if __name__ == '__main__':
    main()
