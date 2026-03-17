import asyncio  # noqa: I001
import base64
import logging
import subprocess
import time
import uuid

import httpx

import test_suite

from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    FilePart,
    FileWithBytes,
    Message,
    Part,
    Role,
    TransportProtocol,
)
from agents.python.v03.pyproto import instruction_pb2


logger = logging.getLogger(__name__)


def _clean_ports(*ports: int) -> None:
    """Forcefully kills processes on host ports to ensure fresh startup.

    Args:
        *ports: Variable length argument list of port numbers (as integers) to clean up.
    """
    for port in ports:
        subprocess.run(  # noqa: S603
            ['fuser', '-k', f'{port}/tcp'],  # noqa: S607
            capture_output=True,
            check=False,
        )


def _log_process_output(
    proc: subprocess.Popen, name: str, err: Exception | None = None
) -> None:
    """Helper to log some output from a process if it fails or for debugging.

    Args:
        proc: The process from which to read standard output.
        name: A human-readable identifier for the process being logged.
        err: Optional exception to log and raise.
    """
    try:
        # Read available output without blocking
        output = proc.stdout.read() if proc.stdout else ''
        if output:
            logger.error(
                '--- %s Output ---\n%s\n-------------------', name, output
            )
    except Exception:  # noqa: BLE001
        logger.debug('Failed to read %s output', name, exc_info=True)
    finally:
        if err:
            logger.error('Error: %s', err)
        raise err


def _wrap_instruction(instruction: instruction_pb2.Instruction) -> Message:
    """Wraps a proto instruction into an A2A Message for transport.

    Args:
        instruction: The instruction protobuf to wrap.

    Returns:
        Message: An initialized A2A Message with the serialized instruction logic.
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


async def _check_agent_ready(
    name: str, url: str, timeout_seconds: int = 35
) -> bool:
    """Use A2A SDK to verify agent readiness by attempting to connect.

    Args:
        name: Name of the agent.
        url: The URL pointing to the agent's well-known root.
        timeout_seconds: Duration in seconds to wait for readiness. Defaults to 35.

    Returns:
        bool: True if connected successfully within the timeout, otherwise False.
    """
    start = time.time()
    async with httpx.AsyncClient(timeout=10) as http_client:
        config = ClientConfig()
        config.httpx_client = http_client
        while time.time() - start < timeout_seconds:
            try:
                # ClientFactory.connect resolves the card and verifies connectivity
                client = await ClientFactory.connect(url, client_config=config)
                if client:
                    logger.info('%s is ready at %s', name, url)
                    return True
            except Exception:  # noqa: BLE001
                logger.debug('%s at %s not ready yet', name, url, exc_info=True)
            await asyncio.sleep(1.0)
    return False


async def start_itk_cluster(
    sdks: list[str],
) -> tuple[list[subprocess.Popen], list[str], list[int]]:
    """Starts a cluster of agents and waits for readiness.

    Args:
        sdks: List of SDK identifiers to launch.

    Returns:
        tuple: (list of Popen processes, list of card URIs, list of ports).
    """
    agent_procs = []
    ports = []
    agent_card_uris = []

    logger.info('Initializing agent cluster with SDKs: %s', ', '.join(sdks))

    try:
        for sdk in sdks:
            test_suite.allocate_agent_ports(sdk)
            agent_def = test_suite.get_agent_def(sdk)
            h_port = agent_def['httpPort']
            g_port = agent_def['grpcPort']
            ports.extend([h_port, g_port])

            _clean_ports(h_port, g_port)

            launcher = test_suite.get_agent_launcher(sdk)
            uri = test_suite.get_agent_card_uri(sdk)
            agent_card_uris.append(uri)

            logger.info('Starting %s agent...', sdk)
            proc = launcher()
            agent_procs.append(proc)

            logger.info('Verifying %s readiness at %s...', sdk, uri)
            if not await _check_agent_ready(sdk, uri):
                err = RuntimeError(f'{sdk} agent failed SDK readiness check.')
                _log_process_output(proc, sdk, err)

    except Exception:
        for proc in agent_procs:
            proc.terminate()
        _clean_ports(*ports)
        raise
    else:
        return agent_procs, agent_card_uris, ports


async def execute_itk_test(  # noqa: PLR0913
    sdks: list[str],
    traversal: str,
    edges: list[str] | None = None,
    scenario_name: str | None = None,
    protocols: list[str] | None = None,
    streaming: bool = False,
) -> bool:
    """Executes a traversal test against an ALREADY RUNNING cluster.

    Args:
        sdks: List of SDK identifiers to include in the test.
        traversal: Name of the graph traversal algorithm.
        edges: Optional custom edges.
        scenario_name: Optional label for logging.
        protocols: Optional list of protocols to test.
        streaming: Whether to use streaming.
    """
    label = scenario_name or traversal
    (
        test_instruction,
        expected_end_tokens,
    ) = test_suite.create_test_suite(
        sdks,
        logger,
        traversal,
        edges=edges,
        protocols=protocols,
        streaming=streaming,
    )

    logger.info('Executing %s traversal test...', label)
    logger.info('Test instruction: %s', test_instruction)
    msg = _wrap_instruction(test_instruction)

    async with httpx.AsyncClient(timeout=120) as http_client:
        config = ClientConfig()
        config.httpx_client = http_client
        config.supported_transports = [TransportProtocol.jsonrpc]
        config.streaming = streaming

        client = await ClientFactory.connect(
            test_suite.get_agent_card_uri(sdks[0]), client_config=config
        )

        responses = []
        logger.info(
            'Dispatching %s payload to %s via JSON-RPC...',
            label,
            test_suite.get_agent_card_uri(sdks[0]),
        )
        async for resp in client.send_message(msg):
            logger.info('!!!!!!!!!!!!Received response: %s!!!!!!!!!!!!!', resp)
            item = resp
            if isinstance(resp, tuple):
                for i in resp:
                    if i is not None:
                        item = i
                        break

            message = None
            if isinstance(item, Message):
                message = item
            elif hasattr(item, 'status') and getattr(
                item.status, 'message', None
            ):
                message = item.status.message

            if message:
                for part in message.parts:
                    p_root = getattr(part, 'root', part)
                    if hasattr(p_root, 'text') and p_root.text:
                        responses.append(p_root.text)

        full_response = ''.join(responses).strip()
        logger.info('Test Result for %s: %s', label, full_response)

        if all(token in full_response for token in expected_end_tokens):
            logger.info('--- INTEGRATION TEST PASSED: %s ---', label)
            return True
        logger.error(
            '--- INTEGRATION TEST FAILED: Verification tokens missing for %s ---',
            label,
        )
        return False


async def run_itk_test(
    sdks: list[str],
    traversal: str,
    edges: list[str] | None = None,
    scenario_name: str | None = None,
) -> bool:
    """Executes a multi-agent integration test traversal.

    Args:
        sdks: List of SDK identifiers to include in the test cluster.
        traversal: Name of the graph traversal algorithm to use.
        edges: Optional list of custom graph edges (e.g., "0->1").
        scenario_name: Optional human-readable name for logging.

    Raises:
        RuntimeError: If an agent fails to start or the test verification fails.
    """
    procs, _, ports = await start_itk_cluster(sdks)
    try:
        return await execute_itk_test(sdks, traversal, edges, scenario_name)
    finally:
        logger.info(
            'Decommissioning agents for %s...', scenario_name or traversal
        )
        for proc in procs:
            proc.terminate()
        _clean_ports(*ports)
