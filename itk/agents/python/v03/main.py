import asyncio  # noqa: I001
import base64
import logging
import signal
import uuid

from collections.abc import AsyncIterator, Callable
from typing import Any

import click
import grpc
import httpx
import uvicorn

from fastapi import FastAPI
from agents.python.v03.pyproto import instruction_pb2

from a2a.client import ClientConfig, ClientFactory
from a2a.grpc import a2a_pb2_grpc
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AFastAPIApplication, A2ARESTFastAPIApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler, GrpcHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    FilePart,
    FileWithBytes,
    Message,
    Part,
    Role,
    TextPart,
    TransportProtocol,
)
from a2a.utils import new_agent_text_message


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def wrap_instruction_to_request(
    instruction: instruction_pb2.Instruction,
) -> Message:
    """Wraps an Instruction proto in an A2A Message.

    Args:
        instruction: The Instruction protobuf to wrap inside the message.

    Returns:
        Message: An A2A Message containing the serialized instruction as a byte file part.

    """
    inst_bytes = instruction.SerializeToString()
    b64_inst = base64.b64encode(inst_bytes).decode('utf-8')

    return Message(
        role=Role.user,
        message_id=str(uuid.uuid4()),
        parts=[
            Part(
                root=FilePart(
                    file=FileWithBytes(
                        bytes=b64_inst,
                        mime_type='application/x-protobuf',
                        name='instruction.bin',
                    )
                )
            )
        ],
    )


async def get_client_with_transport(
    http_client: httpx.AsyncClient, url: str, transport: TransportProtocol | str
) -> Any:
    """Resolves the agent card and returns an A2AClient configured with the specified transport.

    Args:
        http_client: An asynchronous HTTPX client used for communication.
        url: The URL pointing to the agent's well-known card endpoint.
        transport: The requested transport protocol (e.g., 'jsonrpc', 'grpc', 'http_json').

    Returns:
        Any: An initialized A2A client bound to the specified transport.

    Raises:
        ValueError: If the specified transport is not supported or recognized.

    """
    transport_map = {
        'jsonrpc': TransportProtocol.jsonrpc,
        'http_json': TransportProtocol.http_json,
        'grpc': TransportProtocol.grpc,
    }
    if not isinstance(transport, TransportProtocol):
        transport = transport_map.get(
            transport.lower() if isinstance(transport, str) else transport
        )

    if not transport:
        raise ValueError(f'Unsupported transport: {transport}')

    config = ClientConfig()
    config.httpx_client = http_client
    config.grpc_channel_factory = grpc.aio.insecure_channel
    config.supported_transports = [transport]
    config.use_client_preference = True
    config.streaming = False

    return await ClientFactory.connect(url, client_config=config)


async def handle_instruction(
    instruction: instruction_pb2.Instruction,
    call_agent_func: Callable[[instruction_pb2.CallAgent], AsyncIterator[str]],
) -> list[str]:
    """Processes a single Instruction proto recursively.

    Args:
        instruction: The starting Instruction protobuf.
        call_agent_func: An asynchronous callable that handles executing call_agent steps.

    Returns:
        list[str]: A list of string responses gathered from processing the instruction.

    Raises:
        ValueError: If the instruction type is neither call_agent, return_response, nor steps.

    """
    if instruction.HasField('call_agent'):
        return [p async for p in call_agent_func(instruction.call_agent)]
    if instruction.HasField('return_response'):
        return [instruction.return_response.response]
    if instruction.HasField('steps'):
        results = []
        for step in instruction.steps.instructions:
            results.extend(await handle_instruction(step, call_agent_func))
        return results
    raise ValueError('Unknown instruction type')


class V03AgentExecutor(AgentExecutor):
    """Simplified AgentExecutor for ITK v0.3 logic."""

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Implementation of the AgentExecutor interface.

        Args:
            context: The request context containing the incoming message.
            event_queue: The event queue to send responses to.

        """
        instruction = None
        # Extract proto from message parts
        for part in context.message.parts:
            part_root = part.root
            if isinstance(part_root, FilePart) and isinstance(
                part_root.file, FileWithBytes
            ):
                try:
                    raw_bytes = base64.b64decode(part_root.file.bytes)
                    instruction = instruction_pb2.Instruction()
                    instruction.ParseFromString(raw_bytes)
                    break
                except Exception:
                    logger.exception('Failed to parse Instruction proto')
                    continue

        if not instruction:
            logger.error('No valid Instruction found in message parts')
            await event_queue.enqueue_event(
                new_agent_text_message(
                    'Error: No valid Instruction found in request.'
                )
            )
            return

        async def call_agent_func(
            call_agent_proto: instruction_pb2.CallAgent,
        ) -> AsyncIterator[str]:
            logger.info(
                'Calling outbound agent: %s via %s',
                call_agent_proto.agent_card_uri,
                call_agent_proto.transport,
            )
            async with httpx.AsyncClient(timeout=30) as http_client:
                client = await get_client_with_transport(
                    http_client,
                    call_agent_proto.agent_card_uri,
                    call_agent_proto.transport,
                )
                msg = wrap_instruction_to_request(call_agent_proto.instruction)
                async for response in client.send_message(msg):
                    if isinstance(response, Message):
                        text = '\n'.join(
                            p.root.text
                            for p in response.parts
                            if isinstance(p.root, TextPart)
                        )
                        yield text

        try:
            result = await handle_instruction(instruction, call_agent_func)
            await event_queue.enqueue_event(
                new_agent_text_message('\n'.join(result))
            )
        except Exception:
            logger.exception('Instruction execution failed')
            await event_queue.enqueue_event(
                new_agent_text_message(
                    'Execution Error: instruction handling failed'
                )
            )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Implementation of cancel request method required by AgentExecutor interface.

        Args:
            context: The request context containing the incoming message.
            event_queue: The event queue to send responses to.

        """


async def create_grpc_server(
    agent_card: AgentCard,
    request_handler: DefaultRequestHandler,
    host: str,
    port: int,
) -> grpc.aio.Server:
    """Creates and configures the gRPC server.

    Args:
        agent_card: The AgentCard specifying the server's identity and capabilities.
        request_handler: The request handler used for routing and handling instructions.
        host: The host address to bind the server to (e.g., '127.0.0.1').
        port: The port to bind the gRPC server.

    Returns:
        grpc.aio.Server: An initialized gRPC Server object.

    """
    server = grpc.aio.server()
    a2a_pb2_grpc.add_A2AServiceServicer_to_server(
        GrpcHandler(agent_card, request_handler), server
    )
    server.add_insecure_port(f'{host}:{port}')
    return server


def create_http_server(
    agent_card: AgentCard,
    request_handler: DefaultRequestHandler,
    host: str,
    port: int,
) -> uvicorn.Server:
    """Creates and configures the HTTP server for JSON-RPC and REST via FastAPI.

    Args:
        agent_card: The AgentCard specifying the server's identity and capabilities.
        request_handler: The request handler used for routing and handling instructions.
        host: The host address to bind the server to (e.g., '127.0.0.1').
        port: The port to bind the HTTP server.

    Returns:
        uvicorn.Server: An initialized Uvicorn Server instance holding the FastAPI app.

    """
    app = FastAPI(title='ITK v03 Agent Server (Consolidated)')
    A2AFastAPIApplication(agent_card, request_handler).add_routes_to_app(app)
    app.mount(
        '/rest', A2ARESTFastAPIApplication(agent_card, request_handler).build()
    )
    return uvicorn.Server(
        uvicorn.Config(app, host=host, port=port, log_config=None)
    )


async def _run_agent(http_port: int, grpc_port: int) -> None:
    host = '127.0.0.1'

    skill = AgentSkill(
        id='itk_v03_proto_skill',
        name='ITK v03 Proto Skill',
        description='Handles raw byte Instruction protos in v03 subproject.',
        tags=['proto', 'v03', 'itk'],
        examples=['Roll a dice', 'Call another agent'],
    )

    agent_card = AgentCard(
        name='ITK v03 Agent',
        description='Multi-transport agent supporting raw Instruction protos (Consolidated).',
        url=f'http://{host}:{http_port}',
        version='0.3.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=False),
        skills=[skill],
        preferred_transport=TransportProtocol.jsonrpc,
        additional_interfaces=[
            AgentInterface(
                url=f'http://{host}:{http_port}/rest',
                transport=TransportProtocol.http_json,
            ),
            AgentInterface(
                url=f'{host}:{grpc_port}', transport=TransportProtocol.grpc
            ),
        ],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=V03AgentExecutor(), task_store=InMemoryTaskStore()
    )

    http_server = create_http_server(
        agent_card, request_handler, host, http_port
    )
    grpc_server = await create_grpc_server(
        agent_card, request_handler, host, grpc_port
    )

    # Signal handling
    loop = asyncio.get_running_loop()

    async def shutdown() -> None:
        logger.info('Shutting down...')
        http_server.should_exit = True
        await grpc_server.stop(5)

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))

    await grpc_server.start()
    await asyncio.gather(
        http_server.serve(), grpc_server.wait_for_termination()
    )


@click.command()
@click.option('--httpPort', 'http_port', default=10101)
@click.option('--grpcPort', 'grpc_port', default=11001)
def main(http_port: int, grpc_port: int) -> None:
    """Command line entry point for starting the ITK v03 merged Agent.

    Args:
        http_port: The HTTP port to listen on for REST/JSON-RPC calls.
        grpc_port: The gRPC port to listen on.

    """
    asyncio.run(_run_agent(http_port, grpc_port))


if __name__ == '__main__':
    main()
