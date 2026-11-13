"""Helper utilities to host an A2A agent using the SDK server stack.

Minimal helpers to create a Starlette app with `DefaultRequestHandler` and run Uvicorn.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import uvicorn  # type: ignore

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard
from google.protobuf.json_format import ParseDict
from starlette.applications import Starlette


if TYPE_CHECKING:
    from a2a.server.agent_execution import AgentExecutor


def build_starlette_app(
    agent_card: AgentCard | dict,
    *,
    executor: AgentExecutor,
) -> Starlette:
    """Create and return a ready-to-serve Starlette ASGI application.

    Args:
        agent_card: Either a raw ``dict`` or an :class:`a2a.types.AgentCard`
            instance describing the agent.
        executor: Concrete implementation of the A2A ``AgentExecutor``
            interface that will handle incoming requests.

    Returns:
        Starlette: Configured Starlette application with the SDK request handler
        mounted at ``/a2a/v1``.
    """
    # Ensure we have a protobuf AgentCard instance.
    if isinstance(agent_card, dict):
        agent_card = ParseDict(agent_card, AgentCard())

    # Validate executor ---------------------------------------------------------
    if executor is None:
        raise ValueError('executor must be supplied')

    handler = DefaultRequestHandler(executor, InMemoryTaskStore(), agent_card)
    routes = []
    routes.extend(create_agent_card_routes(agent_card))
    routes.extend(create_jsonrpc_routes(handler, '/a2a/v1'))
    return Starlette(routes=routes)


def run_agent_blocking(
    name: str,
    port: int,
    agent_card: AgentCard | dict,
    *,
    executor: AgentExecutor,
) -> None:
    """Spin up a Uvicorn server for the given agent and block the current thread.

    Args:
        name: Human-readable agent name printed on start-up.
        port: TCP port to bind to.
        agent_card: Metadata describing the agent (``dict`` or ``AgentCard``).
        executor: Instance of an ``AgentExecutor`` to handle requests.
    """
    app = build_starlette_app(agent_card, executor=executor)
    print(f'{name} listening on http://localhost:{port}')
    uvicorn.run(app, host='127.0.0.1', port=port, log_level='error')
