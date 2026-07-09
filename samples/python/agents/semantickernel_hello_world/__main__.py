import logging

import click
import httpx

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore
)
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agent_executor import SemanticKernelCalculatorAgentExecutor
from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


@click.command()
@click.option('--host', default='localhost')
@click.option('--port', default=10020)
def main(host, port):
    """Starts the Semantic Kernel Agent server using A2A."""
    httpx_client = httpx.AsyncClient()
    push_config_store = InMemoryPushNotificationConfigStore()
    push_sender = BasePushNotificationSender(httpx_client=httpx_client,
                        config_store=push_config_store)
    request_handler = DefaultRequestHandler(
        agent_executor=SemanticKernelCalculatorAgentExecutor(),
        task_store=InMemoryTaskStore(),
        push_sender=push_sender,
    )

    server = A2AStarletteApplication(
        agent_card=get_agent_card(host, port), http_handler=request_handler
    )
    import uvicorn

    uvicorn.run(server.build(), host=host, port=port)


def get_agent_card(host: str, port: int):
    """Returns the Agent Card for the Semantic Kernel Travel Agent."""
    # Build the agent card
    capabilities = AgentCapabilities(streaming=True)
    skill_calculator = AgentSkill(
        id='calculator',
        name='Semantic Kernel Calculator',
        description=(
            'Handles comprehensive calculations, including currency conversions, distance calculations, and more.'
        ),
        tags=['calculator', 'math', 'semantic-kernel'],
        examples=[
            'What is 2 + 2?',
            'What is 500 * 20 + 5?'
        ],
    )

    agent_card = AgentCard(
        name='Calculator Agent',
        description=(
            'Semantic Kernel-based calculator agent providing comprehensive calculation services '
            'including currency conversion and mathematical problem solving.'
        ),
        url=f'http://{host}:{port}/',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=capabilities,
        skills=[skill_calculator],
    )

    return agent_card


if __name__ == '__main__':
    main()
