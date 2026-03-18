import asyncio
import json
import logging
import os
import sys

from pathlib import Path

import click
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.protobuf.json_format import ParseDict

from skills_agent.agent import root_agent
from skills_agent.agent_executor import CurrencyAgentExecutor


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


async def start_server(host: str, port: int) -> None:
    """Starts the A2A server with the specified host and port."""
    if not os.getenv('GOOGLE_API_KEY'):
        logger.error('GOOGLE_API_KEY must be set')
        sys.exit(1)

    base_path = Path(__file__).parent
    card_path = base_path / 'agent_card.json'
    with card_path.open(encoding='utf-8') as f:
        data = json.load(f)
    agent_card = ParseDict(data, AgentCard(), ignore_unknown_fields=True)

    task_store = InMemoryTaskStore()

    runner = Runner(
        app_name=root_agent.name,
        agent=root_agent,
        session_service=InMemorySessionService(),
    )

    request_handler = DefaultRequestHandler(
        agent_executor=CurrencyAgentExecutor(runner),
        task_store=task_store,
    )

    a2a_app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
        enable_v0_3_compat=True,
    )
    app = a2a_app.build()

    config = uvicorn.Config(app, host=host, port=port, log_level='info')
    server = uvicorn.Server(config)
    await server.serve()


@click.command()
@click.option('--host', default='localhost')
@click.option('--port', default=10999)
def run(host: str, port: int) -> None:
    """Run the A2A business agent server.

    Args:
        host: The host to bind to.
        port: The port to listen on.

    """
    asyncio.run(start_server(host, port))


if __name__ == '__main__':
    run()
