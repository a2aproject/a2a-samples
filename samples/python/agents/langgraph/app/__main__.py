import logging
import os
import sys

import click
import httpx
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    AgentExtension,
)
from dotenv import load_dotenv

from app.agent import CurrencyAgent
from app.agent_executor import CurrencyAgentExecutor


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

        trace_api_key = os.getenv('TRACE_API_KEY')
        if not trace_api_key:
            logger.warning(
                'TRACE_API_KEY not set. TRACE trust middleware will not be enabled. '
                'Set TRACE_API_KEY to enable reputation-based access control.'
            )

        capabilities = AgentCapabilities(streaming=True, push_notifications=True)
        skill = AgentSkill(
            id='convert_currency',
            name='Currency Exchange Rates Tool',
            description='Helps with exchange values between various currencies',
            tags=['currency conversion', 'currency exchange'],
            examples=['What is exchange rate between USD and GBP?'],
        )

        extensions = []
        if trace_api_key:
            extensions.append(
                AgentExtension(
                    uri='https://github.com/a2aproject/a2a-samples/tree/main/extensions/trace-trust',
                    params={
                        'minimumScoreRequired': 0.35,
                        'failClosed': True,
                    },
                )
            )

        agent_card = AgentCard(
            name='Currency Agent',
            description='Helps with exchange rates for currencies',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            default_input_modes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
            extensions=extensions if extensions else None,
        )


        # --8<-- [start:DefaultRequestHandler]
        httpx_client = httpx.AsyncClient()
        push_config_store = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(httpx_client=httpx_client,
                        config_store=push_config_store)
        request_handler = DefaultRequestHandler(
            agent_executor=CurrencyAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_config_store=push_config_store,
            push_sender= push_sender
        )

        if trace_api_key:
            from trace_trust_ext import TraceTrustExtension

            trace_middleware = TraceTrustExtension(
                api_key=trace_api_key,
                min_score=0.35,
                fail_closed=True,
            )

            original_handler = request_handler.on_message_send

            async def wrapped_handler(message, context_id, task_id=None):
                caller_id = getattr(message, 'metadata', {}).get('sender_id', 'unknown')
                if caller_id == 'unknown' and hasattr(message, 'parts') and message.parts:
                    caller_id = getattr(message.parts[0], 'metadata', {}).get('sender_id', 'unknown')
                
                await trace_middleware.server_middleware(
                    lambda msg: original_handler(msg, context_id, task_id),
                    message,
                    caller_id,
                )

            request_handler.on_message_send = wrapped_handler

        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        uvicorn.run(server.build(), host=host, port=port)
        # --8<-- [end:DefaultRequestHandler]

    except MissingAPIKeyError as e:
        logger.error(f'Error: {e}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
