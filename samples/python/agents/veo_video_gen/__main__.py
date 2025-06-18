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
)
from agent import VideoGenerationAgent
from agent_executor import VideoGenerationAgentExecutor
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option(
    '--host', default='localhost', help='Hostname to bind the server to.'
)
@click.option(
    '--port', default=10003, help='Port to bind the server to.'
)  # Changed port from 10002
def main(host: str, port: int):
    try:
        use_vertex_ai = (
            os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'FALSE').upper() == 'TRUE'
        )

        if use_vertex_ai:
            if not os.getenv('GOOGLE_CLOUD_PROJECT'):
                raise Exception(
                    'GOOGLE_CLOUD_PROJECT environment variable not set, but GOOGLE_GENAI_USE_VERTEXAI is TRUE. '
                    'Vertex AI requires a project ID.'
                )
            if not os.getenv('GOOGLE_CLOUD_LOCATION'):
                raise Exception(
                    'GOOGLE_CLOUD_LOCATION environment variable not set, but GOOGLE_GENAI_USE_VERTEXAI is TRUE. '
                    'Vertex AI requires a location (e.g., us-central1).'
                )
            logger.info(
                f'Using Vertex AI with project: {os.getenv("GOOGLE_CLOUD_PROJECT")} and location: {os.getenv("GOOGLE_CLOUD_LOCATION")}'
            )
        else:  # Not using Vertex AI, so API key is expected
            logger.error(
                'Vertex AI is required for this agent. Please set GOOGLE_GENAI_USE_VERTEXAI to TRUE and configure GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION.'
            )

        # Check for GCS bucket name (critical for video output)
        if not os.getenv(VideoGenerationAgent.GCS_BUCKET_NAME_ENV_VAR):
            raise Exception(
                f'{VideoGenerationAgent.GCS_BUCKET_NAME_ENV_VAR} environment variable not set. '
                'This is required for storing generated videos.'
            )
        logger.info(
            f'Using GCS bucket: {os.getenv(VideoGenerationAgent.GCS_BUCKET_NAME_ENV_VAR)}'
        )

        if os.getenv(VideoGenerationAgent.SIGNER_SERVICE_ACCOUNT_EMAIL_ENV_VAR):
            logger.info(
                f'Using signer service account: {os.getenv(VideoGenerationAgent.SIGNER_SERVICE_ACCOUNT_EMAIL_ENV_VAR)} for GCS signed URLs.'
            )
        else:
            logger.info(
                'No SIGNER_SERVICE_ACCOUNT_EMAIL set. Ambient credentials will be used for GCS signed URLs. '
                "Ensure the runtime identity has 'Service Account Token Creator' role on itself or the target SA if impersonation is intended via ADC."
            )

        # Agent Card Configuration
        capabilities = AgentCapabilities(
            streaming=True
        )  # Agent supports streaming updates

        skill = AgentSkill(
            id='generate_video_from_prompt',
            name='Generate Video from Text Prompt (VEO)',
            description='Generates a video based on a textual description using VEO. '
            'Provides progress updates and a link to the final video.',
            tags=['video', 'generation', 'multimodal', 'veo'],
            examples=[
                'Create a video of a futuristic cityscape at sunset.',
                'Generate a short clip of a cat playing with a yarn ball in a sunny room.',
            ],
        )

        agent_card = AgentCard(
            name='VEO Video Generation Agent',
            description="This agent uses Google's VEO model to generate videos from text prompts and provides a GCS link to the output.",
            url=f'http://{host}:{port}/',  # A2A endpoint URL
            version='1.0.0',
            defaultInputModes=VideoGenerationAgent.SUPPORTED_INPUT_CONTENT_TYPES,
            defaultOutputModes=VideoGenerationAgent.SUPPORTED_OUTPUT_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        request_handler = DefaultRequestHandler(
            agent_executor=VideoGenerationAgentExecutor(),
            task_store=InMemoryTaskStore(),  # Using in-memory task store for this example
        )

        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        logger.info(
            f'Starting VEO Video Generation Agent server on http://{host}:{port}'
        )

        import uvicorn

        uvicorn.run(server.build(), host=host, port=port)

    except ImportError as e:
        logger.error(
            f"Import Error: {e}. Please ensure all dependencies like 'google-cloud-storage' and 'google-generativeai' are installed."
        )
        exit(1)
    except Exception as e:
        logger.error(
            f'An unexpected error occurred during server startup: {e}',
            exc_info=True,
        )
        exit(1)


if __name__ == '__main__':
    main()
