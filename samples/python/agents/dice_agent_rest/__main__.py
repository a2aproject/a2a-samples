import logging
import os

import click
import uvicorn

from a2a.server.apps import A2ARESTFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    TransportProtocol,
)
from agent_executor import DiceAgentExecutor  # type: ignore[import-untyped]
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig()


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10101)
def main(host: str, port: int) -> None:
    # Verify an API key is set.
    # Not required if using Vertex AI APIs.
    if os.getenv('GOOGLE_GENAI_USE_VERTEXAI') != 'TRUE' and not os.getenv(
        'GOOGLE_API_KEY'
    ):
        raise ValueError(
            'GOOGLE_API_KEY environment variable not set and '
            'GOOGLE_GENAI_USE_VERTEXAI is not TRUE.'
        )

    skills = [
        AgentSkill(
            id='f56cab88-3fe9-47ec-ba6e-86a13c9f1f74',
            name='Roll Dice',
            description='Rolls an N sided dice and returns the result. By default uses a 6 sided dice.',
            tags=['dice'],
            examples=['Can you roll an 11 sided dice?'],
        ),
        AgentSkill(
            id='33856129-d686-4a54-9c6e-fffffec3561b',
            name='Prime Detector',
            description='Determines which numbers from a list are prime numbers.',
            tags=['prime'],
            examples=['Which of these are prime numbers 1, 4, 6, 7'],
        ),
    ]

    agent_card = AgentCard(
        name='Dice Agent',
        description='An agent that can roll arbitrary dice and answer if numbers are prime',
        url=f'http://{host}:{port}/',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=skills,
        preferred_transport=TransportProtocol.http_json,
    )

    agent_executor = DiceAgentExecutor()
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, task_store=InMemoryTaskStore()
    )

    server = A2ARESTFastAPIApplication(
        agent_card=agent_card, http_handler=request_handler
    )

    uvicorn.run(server.build(), host=host, port=port)


if __name__ == '__main__':
    main()
