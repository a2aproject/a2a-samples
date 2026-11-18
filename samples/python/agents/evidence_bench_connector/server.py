"""A2A 1.0 server for the Evidence Bench connector sample."""

from __future__ import annotations

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from starlette.applications import Starlette

from evidence_bench_connector.agent_executor import (
    EvidenceBenchConnectorExecutor,
    RemoteRunner,
)


def build_agent_card(public_url: str) -> AgentCard:
    """Build the connector's explicit stable A2A 1.0 Agent Card."""
    skill = AgentSkill(
        id='evidence-bench-delegation',
        name='Evidence Bench scientific analysis',
        description=(
            'Delegate a scientific task to a separately deployed Evidence Bench '
            'service and return its bounded report and run summary.'
        ),
        tags=['a2a', 'science', 'delegation', 'provenance'],
        examples=['Analyze the attached CSV and report effect sizes and limitations.'],
        input_modes=['text/plain', 'application/octet-stream'],
        output_modes=['text/markdown', 'application/json'],
    )
    return AgentCard(
        name='Evidence Bench Connector',
        description=(
            'A thin A2A connector to a user-operated Evidence Bench deployment; '
            'this sample is not the scientific engine.'
        ),
        version='0.1.0',
        default_input_modes=['text/plain', 'application/octet-stream'],
        default_output_modes=['text/markdown', 'application/json'],
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[
            AgentInterface(
                protocol_binding='JSONRPC',
                url=public_url.rstrip('/'),
                protocol_version='1.0',
            )
        ],
        skills=[skill],
    )


def create_app(remote: RemoteRunner, public_url: str) -> Starlette:
    """Create a testable ASGI application with an injected remote boundary."""
    card = build_agent_card(public_url)
    handler = DefaultRequestHandler(
        agent_executor=EvidenceBenchConnectorExecutor(remote),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    routes = [
        *create_agent_card_routes(card),
        *create_jsonrpc_routes(handler, '/'),
    ]
    return Starlette(routes=routes)
