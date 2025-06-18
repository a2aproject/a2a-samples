import logging

import click
import httpx

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agent_executor import CurrencyAgentExecutor
from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


@click.command()
@click.option('--host', default='localhost')
@click.option('--port', default=47128)  # Updated to a less commonly used port
def main(host, port):
    """Starts the Semantic Kernel Agent server using A2A."""
    logger.info(f'Starting Currency Agent server on {host}:{port}')

    httpx_client = httpx.AsyncClient()
    agent_card = get_agent_card(host, port)

    # Create task store with proper configuration
    task_store = InMemoryTaskStore()
    logger.info('Created task store')

    # Create the executor and request handler with proper configuration
    executor = CurrencyAgentExecutor()
    logger.info('Created agent executor')

    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
        push_notifier=InMemoryPushNotifier(httpx_client),
    )
    logger.info('Created request handler')

    # Configure the server with proper JSON-RPC methods
    server = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    logger.info('Created A2A server application')

    # Add middleware for debugging requests
    app = server.build()

    @app.middleware('http')
    async def log_requests(request, call_next):
        body = await request.body()
        logger.info(f'Incoming request: {request.method} {request.url}')
        logger.info(
            f'Request body: {body.decode("utf-8") if body else "Empty"}'
        )
        response = await call_next(request)
        return response

    import uvicorn

    logger.info(f'Starting uvicorn server at http://{host}:{port}')
    uvicorn.run(app, host=host, port=port)


def get_agent_card(host: str, port: int):
    """Returns the Agent Card for the Azure Foundry Agent Service."""
    # Build the agent card
    capabilities = AgentCapabilities(streaming=True)
    skill_trip_planning = AgentSkill(
        id='currency_exchange_agent',
        name='Currency Exchange Agent',
        description=(
            'Handles currency exchange queries and conversions using real-time exchange rates '
            'from the Frankfurter API. Provides accurate currency conversion rates and travel-related financial advice.'
        ),
        tags=['currency', 'exchange', 'conversion', 'travel', 'finance'],
        examples=[
            'How much is 1 USD to EUR?',
            'What is the current exchange rate for USD to JPY?',
            'Convert 100 GBP to USD',
        ],
    )

    agent_card = AgentCard(
        name='Currency Exchange Agent',
        description=(
            'A specialized currency exchange agent that provides real-time currency conversion rates '
            'and financial information for travelers and international transactions.'
        ),
        url=f'http://{host}:{port}/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=capabilities,
        skills=[skill_trip_planning],
    )

    return agent_card


if __name__ == '__main__':
    main()
