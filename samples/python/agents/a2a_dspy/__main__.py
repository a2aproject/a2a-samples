from __future__ import annotations

import logging

import click
import uvicorn
from starlette.middleware.cors import CORSMiddleware

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from executor import DspyAgentExecutor


logger = logging.getLogger(__name__)
logging.basicConfig()

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10020)
def main(host: str, port: int):
    """A2A DSPy Sample Server with Bearer Token Authentication."""
    skill = AgentSkill(
        id='dspy_agent',
        name='DSPy Agent',
        description='A simple DSPy agent that can answer questions and remember user interactions.',
        tags=['DSPy', 'Memory', 'Mem0'],
        examples=[
            'What is the capital of France?',
            'What did I ask you about earlier?',
            'Remember that I prefer morning meetings.',
        ],
    )

    agent_executor = DspyAgentExecutor()
    agent_card = AgentCard(
        name='DSPy Agent',
        description='A simple DSPy agent that can answer questions and remember user interactions.',
        url=f'http://{host}:{port}/',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, task_store=InMemoryTaskStore()
    )

    server = A2AStarletteApplication(agent_card, request_handler)
    starlette_app = server.build()
    
    starlette_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    uvicorn.run(starlette_app, host=host, port=port)


if __name__ == '__main__':
    main()
