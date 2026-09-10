import logging
import os
import sys

import click
import httpx
import uvicorn

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from dotenv import load_dotenv
from starlette.applications import Starlette

from app.agent import CurrencyAgent
from app.agent_executor import CurrencyAgentExecutor


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


def _validate_env() -> None:
    if os.getenv('MODEL_SOURCE', 'google') == 'google':
        if not os.getenv('GOOGLE_API_KEY'):
            raise MissingAPIKeyError('GOOGLE_API_KEY environment variable not set.')
    else:
        if not os.getenv('TOOL_LLM_URL'):
            raise MissingAPIKeyError('TOOL_LLM_URL environment variable not set.')
        if not os.getenv('TOOL_LLM_NAME'):
            raise MissingAPIKeyError('TOOL_LLM_NAME environment variable not set.')


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10000)
def main(host: str, port: int) -> None:
    """Starts the Currency Agent server."""
    try:
        _validate_env()

        capabilities = AgentCapabilities(streaming=True, push_notifications=True)
        skill = AgentSkill(
            id='convert_currency',
            name='Currency Exchange Rates Tool',
            description='Helps with exchange values between various currencies',
            tags=['currency conversion', 'currency exchange'],
            examples=['What is exchange rate between USD and GBP?'],
        )
        agent_card = AgentCard(
            name='Currency Agent',
            description='Helps with exchange rates for currencies',
            version='1.0.0',
            supported_interfaces=[
                AgentInterface(
                    protocol_binding='JSONRPC',
                    url=f'http://{host}:{port}/',
                    protocol_version='1.0',
                )
            ],
            default_input_modes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        # --8<-- [start:DefaultRequestHandler]
        httpx_client = httpx.AsyncClient()
        push_config_store = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(
            httpx_client=httpx_client, config_store=push_config_store
        )
        request_handler = DefaultRequestHandler(
            agent_executor=CurrencyAgentExecutor(),
            task_store=InMemoryTaskStore(),
            agent_card=agent_card,
            push_config_store=push_config_store,
            push_sender=push_sender,
        )

        routes = []
        routes.extend(create_agent_card_routes(agent_card))
        routes.extend(create_jsonrpc_routes(request_handler, rpc_url='/'))

        app = Starlette(routes=routes)
        uvicorn.run(app, host=host, port=port)
        # --8<-- [end:DefaultRequestHandler]

    except MissingAPIKeyError:
        logger.exception('Missing required API key configuration')
        sys.exit(1)
    except Exception:
        logger.exception('An error occurred during server startup')
        sys.exit(1)


if __name__ == '__main__':
    main()
