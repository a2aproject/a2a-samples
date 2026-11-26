import asyncio
import functools
import logging
import os

from typing import Any

import click
import sqlalchemy
import sqlalchemy.ext.asyncio
import uvicorn

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import DatabaseTaskStore, InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from agent import root_agent as calendar_agent
from agent_executor import ADKAgentExecutor
from dotenv import load_dotenv
from google.cloud.alloydbconnector import AsyncConnector
from starlette.applications import Starlette


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


async def create_sqlalchemy_engine(
    inst_uri: str,
    user: str,
    password: str,
    db: str,
    refresh_strategy: str = 'lazy',
) -> tuple[sqlalchemy.ext.asyncio.engine.AsyncEngine, AsyncConnector]:
    """Create a connection pool for an AlloyDB instance.

    Returns the pool and the connector. Callers are responsible for closing
    the pool and the connector.

    Args:
        inst_uri (str):
            The instance URI specifies the instance relative to the project,
            region, and cluster. For example:
            "projects/my-project/locations/us-central1/clusters/my-cluster/instances/my-instance"
        user (str):
            The database user name, e.g., postgres
        password (str):
            The database user's password, e.g., secret-password
        db (str):
            The name of the database, e.g., mydb
        refresh_strategy (Optional[str]):
            Refresh strategy for the AlloyDB Connector. Can be one of "lazy"
            or "background". For serverless environments use "lazy" to avoid
            errors resulting from CPU being throttled.
    """
    connector = AsyncConnector(refresh_strategy=refresh_strategy)

    # create SQLAlchemy connection pool
    engine = sqlalchemy.ext.asyncio.create_async_engine(
        'postgresql+asyncpg://',
        async_creator=lambda: connector.connect(
            inst_uri,
            'asyncpg',
            user=user,
            password=password,
            db=db,
            ip_type='PUBLIC',
        ),
        execution_options={'isolation_level': 'AUTOCOMMIT'},
    )
    return engine, connector


def make_sync(func: Any) -> Any:
    """Wrap an async Click command so it runs synchronously."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option('--host', default='localhost')
@click.option('--port', default=10002)
@make_sync
async def main(host: str, port: int) -> None:
    """Start the A2A calendar agent server."""
    app_url = os.getenv('APP_URL', f'http://{host}:{port}')
    agent_card = AgentCard(
        name=calendar_agent.name,
        description=calendar_agent.description,
        version='1.0.0',
        default_input_modes=['text', 'text/plain'],
        default_output_modes=['text', 'text/plain'],
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[
            AgentInterface(
                protocol_binding='JSONRPC',
                url=app_url,
                protocol_version='1.0',
            )
        ],
        skills=[
            AgentSkill(
                id='add_calendar_event',
                name='Add Calendar Event',
                description='Creates a new calendar event.',
                tags=['calendar', 'event', 'create'],
                examples=[
                    'Add a calendar event for my meeting tomorrow at 10 AM.',
                ],
            )
        ],
    )

    use_alloy_db_str = os.getenv('USE_ALLOY_DB', 'False')
    if use_alloy_db_str.lower() == 'true':
        db_instance = os.environ['DB_INSTANCE']
        db_name = os.environ['DB_NAME']
        db_user = os.environ['DB_USER']
        db_pass = os.environ['DB_PASS']

        engine, _connector = await create_sqlalchemy_engine(
            db_instance,
            db_user,
            db_pass,
            db_name,
        )
        task_store = DatabaseTaskStore(engine)
    else:
        task_store = InMemoryTaskStore()

    request_handler = DefaultRequestHandler(
        agent_executor=ADKAgentExecutor(
            agent=calendar_agent,
        ),
        task_store=task_store,
        agent_card=agent_card,
    )

    routes = [
        *create_agent_card_routes(agent_card),
        *create_jsonrpc_routes(request_handler, '/'),
    ]
    app = Starlette(
        routes=routes,
        middleware=[],
    )

    config = uvicorn.Config(app, host=host, port=port, log_level='info')
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == '__main__':
    main()
