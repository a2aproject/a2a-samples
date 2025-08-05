"""utils.server
Helper utilities to host an A2A agent using the SDK server stack.

Minimal helpers to create a Starlette app with `DefaultRequestHandler` and run Uvicorn.
"""

from __future__ import annotations

import uvicorn  # type: ignore

from a2a.server.apps.jsonrpc.starlette_app import A2AStarletteApplication
from a2a.server.request_handlers.default_request_handler import (
    DefaultRequestHandler,
)
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import AgentCard


def build_starlette_app(
    agent_card,
    *,
    executor,
):
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
    # Ensure we have a Pydantic AgentCard instance.
    if isinstance(agent_card, dict):
        agent_card = AgentCard.model_validate(agent_card)  # type: ignore[arg-type]

    # Validate executor ---------------------------------------------------------
    if executor is None:
        raise ValueError('executor must be supplied')

    handler = DefaultRequestHandler(executor, InMemoryTaskStore())
    return A2AStarletteApplication(
        agent_card=agent_card, http_handler=handler
    ).build(rpc_url='/a2a/v1')


def run_agent_blocking(
    name: str,
    port: int,
    agent_card,
    *,
    executor,
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
