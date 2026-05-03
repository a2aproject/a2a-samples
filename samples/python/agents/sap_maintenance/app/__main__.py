"""Entry point — starts the SAP Maintenance Order Agent as an A2A server."""

import logging
import sys

import click
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from app.agent_executor import SAPMaintenanceAgentExecutor


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_agent_card(host: str, port: int) -> AgentCard:
    """Build the A2A Agent Card describing this agent's capabilities."""
    return AgentCard(
        name='SAP Maintenance Order Analyst',
        description=(
            'Analyzes SAP S/4HANA maintenance orders — search orders, check '
            'confirmations, view costs, inspect equipment, and manage TECO '
            'status. Uses the PEOS (Planner-Executor-Observer-Synthesiser) '
            'architecture with dynamic tool binding for token-efficient '
            'multi-step analysis.'
        ),
        url=f'http://{host}:{port}/',
        version='1.0.0',
        default_input_modes=['text/plain'],
        default_output_modes=['text/plain'],
        capabilities=AgentCapabilities(
            streaming=True,
            push_notifications=False,
        ),
        skills=[
            AgentSkill(
                id='sap_maintenance_analysis',
                name='SAP Maintenance Order Analysis',
                description=(
                    'Search and analyze SAP S/4HANA maintenance orders. '
                    'Supports order lookup, cost breakdown, confirmation '
                    'status, material stock checks, equipment details, and '
                    'TECO management.'
                ),
                tags=[
                    'sap',
                    'maintenance',
                    'erp',
                    's4hana',
                    'plant-maintenance',
                ],
                examples=[
                    'Show high priority orders for plant 1010',
                    'Get details for order 4000045',
                    'Check stock for material 100-100',
                    'Which orders are ready for TECO?',
                    'Cost breakdown for order 4000045',
                ],
            ),
        ],
    )


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10020)
def main(host: str, port: int) -> None:
    """Start the SAP Maintenance Order Agent A2A server."""
    try:
        agent_card = build_agent_card(host, port)
        request_handler = DefaultRequestHandler(
            agent_executor=SAPMaintenanceAgentExecutor(),
            task_store=InMemoryTaskStore(),
        )
        server = A2AStarletteApplication(
            agent_card=agent_card,
            http_handler=request_handler,
        )
        logger.info(
            'Starting SAP Maintenance Agent on %s:%d (mock mode)',
            host,
            port,
        )
        uvicorn.run(server.build(), host=host, port=port)
    except Exception:
        logger.exception('Server startup failed')
        sys.exit(1)


if __name__ == '__main__':
    main()
