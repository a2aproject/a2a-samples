import asyncio
import logging
import os
import signal

import asyncclick as click
import grpc
import uvicorn

from a2a.grpc import a2a_pb2, a2a_pb2_grpc
from a2a.server.request_handlers import DefaultRequestHandler, GrpcHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    TransportProtocol,
)
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from agent_executor import DiceAgentExecutor  # type: ignore[import-untyped]
from dotenv import load_dotenv
from grpc_reflection.v1alpha import reflection
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route


load_dotenv()

logging.basicConfig(level=logging.INFO)


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--agent-card-port', 'agent_card_port', default=11000)
@click.option('--port', 'port', default=11001)
async def main(host: str, port: int, agent_card_port: int) -> None:
    # Verify an API key is set.
    # Not required if using Vertex AI APIs.
    if os.getenv('GOOGLE_GENAI_USE_VERTEXAI') != 'TRUE' and not os.getenv(
        'GOOGLE_API_KEY'
    ):
        raise ValueError(  # noqa: TRY003
            'GOOGLE_API_KEY environment variable not set and '
            'GOOGLE_GENAI_USE_VERTEXAI is not TRUE.'
        )

    agent_card = get_agent_card(host, port)

    # Create gRPC server
    grpc_server = await create_grpc_server(agent_card, host, port)

    # The gRPC server cannot serve the public agent card at the well-known URL.
    # A separate HTTP server is needed to serve the public agent card, which clients
    # can use as an entry point for discovering the gRPC endpoint.

    # create http server for serving agent card
    http_server = create_agent_card_server(agent_card, host, agent_card_port)

    loop = asyncio.get_running_loop()

    async def shutdown(sig: signal.Signals) -> None:
        """Gracefully shutdown the servers."""
        logging.warning(f'Received exit signal {sig.name}...')
        # Uvicorn server shutdown
        http_server.should_exit = True

        await grpc_server.stop(5)
        logging.warning('Servers stopped.')

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s)))

    await grpc_server.start()

    await asyncio.gather(http_server.serve(), grpc_server.wait_for_termination())


def create_agent_card_server(agent_card: AgentCard, host: str, agent_card_port: int) -> uvicorn.Server:
    """Creates the Starlette app for the agent card server."""

    def get_agent_card_http(request: Request) -> Response:
        return JSONResponse(
            agent_card.model_dump(mode='json', exclude_none=True)
        )
    routes = [
        Route(AGENT_CARD_WELL_KNOWN_PATH, endpoint=get_agent_card_http)
    ]
    app = Starlette(routes=routes)

    # Create uvicorn server for agent card
    config = uvicorn.Config(
        app,
        host=host,
        port=agent_card_port,
        log_config=None,
    )
    logging.info(f'Starting HTTP server on port {agent_card_port}')
    return uvicorn.Server(config)


async def create_grpc_server(agent_card: AgentCard, host: str, port: int) -> grpc.aio.Server:
    """Creates the gRPC server."""
    agent_executor = DiceAgentExecutor()
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, task_store=InMemoryTaskStore()
    )

    server = grpc.aio.server()
    a2a_pb2_grpc.add_A2AServiceServicer_to_server(
        GrpcHandler(agent_card, request_handler),
        server,
    )
    SERVICE_NAMES = (
        a2a_pb2.DESCRIPTOR.services_by_name['A2AService'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    server.add_insecure_port(f'{host}:{port}')
    logging.info(f'Starting gRPC server on port {port}')
    return server

def get_agent_card(host: str, port: int) -> AgentCard:
    """Returns the agent card."""
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

    return AgentCard(
        name='Dice Agent',
        description='An agent that can roll arbitrary dice and answer if numbers are prime',
        url=f'{host}:{port}',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        supports_authenticated_extended_card=True,
        skills=skills,
        preferred_transport=TransportProtocol.grpc,
    )



if __name__ == '__main__':
    main(_anyio_backend='asyncio')
