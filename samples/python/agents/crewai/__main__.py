"""This file serves as the main entry point for the application.

It initializes the A2A server, defines the agent's capabilities,
and starts the server to handle incoming requests.
"""

import logging
import os

import click

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    AgentExtension,
)
from agent import ImageGenerationAgent
from agent_executor import ImageGenerationAgentExecutor
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10001)
def main(host, port):
    """Entry point for the A2A + CrewAI Image generation sample."""
    try:
        if not os.getenv('GOOGLE_API_KEY') and not os.getenv(
            'GOOGLE_GENAI_USE_VERTEXAI'
        ):
            raise MissingAPIKeyError(
                'GOOGLE_API_KEY or Vertex AI environment variables not set.'
            )

        trace_api_key = os.getenv('TRACE_API_KEY')
        if not trace_api_key:
            logger.warning(
                'TRACE_API_KEY not set. TRACE trust middleware will not be enabled. '
                'Set TRACE_API_KEY to enable reputation-based access control.'
            )

        capabilities = AgentCapabilities(streaming=False)
        skill = AgentSkill(
            id='image_generator',
            name='Image Generator',
            description=(
                'Generate stunning, high-quality images on demand and leverage'
                ' powerful editing capabilities to modify, enhance, or completely'
                ' transform visuals.'
            ),
            tags=['generate image', 'edit image'],
            examples=['Generate a photorealistic image of raspberry lemonade'],
        )

        agent_host_url = (
            os.getenv('HOST_OVERRIDE')
            if os.getenv('HOST_OVERRIDE')
            else f'http://{host}:{port}/'
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
            name='Image Generator Agent',
            description=(
                'Generate stunning, high-quality images on demand and leverage'
                ' powerful editing capabilities to modify, enhance, or completely'
                ' transform visuals.'
            ),
            url=agent_host_url,
            version='1.0.0',
            default_input_modes=ImageGenerationAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=ImageGenerationAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
            extensions=extensions if extensions else None,
        )

        request_handler = DefaultRequestHandler(
            agent_executor=ImageGenerationAgentExecutor(),
            task_store=InMemoryTaskStore(),
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
