import asyncio
import logging
import os
import sys

import click
import uvicorn

from dotenv import load_dotenv


load_dotenv()

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCard,
)
from agent_executor import HRAgentExecutor
from api import hr_api
from oauth2_middleware import OAuth2Middleware


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


@click.command()
@click.option('--host', default='0.0.0.0')
@click.option('--port_agent', default=10050)
@click.option('--port_api', default=10051)
def main(host: str, port_agent: int, port_api: int):
    async def run_all():
        await asyncio.gather(
            start_agent(host, port_agent),
            start_api(host, port_api),
        )

    asyncio.run(run_all())


async def start_agent(host: str, port):
    # We define the configuration as a raw dictionary first.
    # This avoids the "no attribute root" error by letting the AgentCard
    # constructor handle the internal Pydantic mapping itself.
    card_config = {
        'name': 'Staff0 HR Agent',
        'description': 'This agent handles external verification requests...',
        'url': f'http://{host}:{port}/',
        'version': '0.1.0',
        'default_input_modes': ['application/json'],
        'default_output_modes': ['application/json'],
        'capabilities': {'streaming': True},
        'skills': [
            {
                'id': 'is_active_employee',
                'name': 'Check Employment Status Tool',
                'description': 'Confirm whether a person is an active employee.',
                'tags': ['employment status'],
                'examples': ['Does John Doe work at Staff0?']
            }
        ],
        'security_schemes': {
            'oauth2_m2m': {
                'type': 'oauth2',
                'flows': {
                    'client_credentials': { # Use snake_case here
                        'token_url': f"https://{os.getenv('HR_AUTH0_DOMAIN')}/oauth/token",
                        'scopes': {
                            'read:employee_status': 'Verify status'
                        }
                    }
                }
            }
        },
        'security': [{'oauth2_m2m': ['read:employee_status']}]
    }

    # Now, pass the WHOLE dictionary into the constructor.
    # The SDK will convert the nested dicts into the proper
    # OAuth2SecurityScheme objects internally.
    agent_card = AgentCard(**card_config)

    request_handler = DefaultRequestHandler(
        agent_executor=HRAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )

    app = server.build()
    app.add_middleware(
        OAuth2Middleware,
        agent_card=agent_card,
        public_paths=[
            '/.well-known/agent.json',
            '/.well-known/agent-card.json'
        ],
    )

    logger.info(f'Starting HR Agent server on {host}:{port}')
    await uvicorn.Server(uvicorn.Config(app=app, host=host, port=port)).serve()


async def start_api(host: str, port):
    logger.info(f'Starting HR API server on {host}:{port}')
    await uvicorn.Server(
        uvicorn.Config(app=hr_api, host=host, port=port)
    ).serve()


# this ensures that `main()` runs when using `uv run .`
if not hasattr(sys, '_called_from_uvicorn'):
    main()
