import logging
import os
import sys

import click
import uvicorn
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
    create_rest_routes,
)
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from dotenv import load_dotenv

from app.agent import CurrencyAgent
from app.agent_executor import CurrencyAgentExecutor
from starlette.applications import Starlette

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10000)
def main(host, port):
    """Starts the Currency Agent server."""
    try:
        if os.getenv('model_source', 'google') == 'google':
            if not os.getenv('GOOGLE_API_KEY'):
                raise MissingAPIKeyError(
                    'GOOGLE_API_KEY environment variable not set.'
                )
        else:
            if not os.getenv('TOOL_LLM_URL'):
                raise MissingAPIKeyError(
                    'TOOL_LLM_URL environment variable not set.'
                )
            if not os.getenv('TOOL_LLM_NAME'):
                raise MissingAPIKeyError(
                    'TOOL_LLM_NAME environment not variable not set.'
                )

        capabilities = AgentCapabilities(
            streaming=True, extended_agent_card=True
        )
        skill = AgentSkill(
            id='convert_currency',
            name='Currency Exchange Rates Tool',
            description='Helps with exchange values between various currencies',
            tags=['currency conversion', 'currency exchange'],
            input_modes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            output_modes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            examples=['What is exchange rate between USD and GBP?'],
        )
        extended_skill = AgentSkill(
            id='convert_currency_extended',
            name='Advanced Currency Exchange Rates Tool',
            description='Extended currency conversion with historical rates and advanced analytics, only for authenticated users.',
            tags=[
                'currency conversion',
                'currency exchange',
                'historical',
                'analytics',
            ],
            input_modes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            output_modes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            examples=['What was the USD to EUR rate last month?'],
        )
        agent_card = AgentCard(
            name='Currency Agent',
            description='Helps with exchange rates for currencies',
            supported_interfaces=[
                AgentInterface(
                    protocol_binding='JSONRPC',
                    url=f'http://{host}:{port}/api/v1/jsonrpc/',
                ),
                AgentInterface(
                    protocol_binding='HTTP+JSON',
                    url=f'http://{host}:{port}/api/v1/rest/',
                ),
            ],
            version='1.0.0',
            default_input_modes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )
        extended_agent_card = AgentCard(
            name='Currency Agent - Extended Edition',
            description='Full-featured currency agent with advanced capabilities for authenticated users.',
            supported_interfaces=[
                AgentInterface(
                    protocol_binding='JSONRPC',
                    url=f'http://{host}:{port}/api/v1/jsonrpc/',
                ),
                AgentInterface(
                    protocol_binding='HTTP+JSON',
                    url=f'http://{host}:{port}/api/v1/rest/',
                ),
            ],
            version='1.0.0',
            default_input_modes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill, extended_skill],
        )

        # --8<-- [start:DefaultRequestHandler]
        request_handler = DefaultRequestHandler(
            agent_executor=CurrencyAgentExecutor(),
            task_store=InMemoryTaskStore(),
            agent_card=agent_card,
            extended_agent_card=extended_agent_card,
        )
        routes = []
        # A2A Agent Card routes
        routes.extend(create_agent_card_routes(agent_card))
        # JSON-RPC routes
        routes.extend(
            create_jsonrpc_routes(request_handler, rpc_url='/api/v1/jsonrpc/')
        )
        routes.extend(
            create_rest_routes(request_handler, path_prefix='/api/v1/rest/')
        )

        server = Starlette(routes=routes)

        uvicorn.run(server, host=host, port=port)
        # --8<-- [end:DefaultRequestHandler]

    except MissingAPIKeyError as e:
        logger.error(f'Error: {e}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
