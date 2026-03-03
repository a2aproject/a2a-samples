import asyncio
import base64
import logging
import subprocess
import sys
import time
import uuid

import click
import httpx

from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    FilePart,
    FileWithBytes,
    Message,
    Part,
    Role,
    TextPart,
    TransportProtocol,
)
from agents.python.v03.pyproto import instruction_pb2
from test_suite import create_test_suite


logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _clean_ports(*ports: str) -> None:
    """Forcefully kills processes on host ports to ensure fresh startup.

    Args:
        *ports: Variable length argument list of port numbers (as strings) to clean up.

    """
    for port in ports:
        subprocess.run(  # noqa: S603
            ['fuser', '-k', f'{port}/tcp'],  # noqa: S607
            capture_output=True,
            check=False,
        )


def log_process_output(proc: subprocess.Popen, name: str) -> None:
    """Helper to log some output from a process if it fails or for debugging.

    Args:
        proc: The process from which to read standard output.
        name: A human-readable identifier for the process being logged.

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


def wrap_instruction(instruction: instruction_pb2.Instruction) -> Message:
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


async def check_agent_ready(
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


async def main_async(sdks: str, traversal: str) -> None:
    """Execute the multi-agent integration test traversal."""
    tested_sdks = [s.strip() for s in sdks.split(',')]
    (
        test_instruction,
        ports,
        agent_launchers,
        agent_card_uris,
        expected_end_tokens,
    ) = create_test_suite(tested_sdks, logger, traversal)
    _clean_ports(*ports)
    agent_procs = [launcher() for launcher in agent_launchers]

    logger.info('Initializing integration test...')

    try:
        logger.info('Waiting for agent cluster stability...')
        # Check readiness using SDK connect
        for sdk, url, agent_proc in zip(
            tested_sdks, agent_card_uris, agent_procs, strict=True
        ):
            is_ready = await check_agent_ready(sdk, url)
            if not is_ready:
                log_process_output(agent_proc, sdk)
                raise RuntimeError(f'{sdk} agent failed SDK readiness check.')  # noqa: TRY301

        logger.info('Cluster ready. Executing cross-SDK traversal test...')

        msg = wrap_instruction(test_instruction)

        async with httpx.AsyncClient(timeout=120) as http_client:
            config = ClientConfig()
            config.httpx_client = http_client
            config.supported_transports = [TransportProtocol.jsonrpc]

            client = await ClientFactory.connect(
                agent_card_uris[0], client_config=config
            )

            responses = []
            logger.info(
                'Dispatching test payload to %s via JSON-RPC...',
                agent_card_uris[0],
            )
            async for resp in client.send_message(msg):
                if isinstance(resp, Message):
                    responses.extend(
                        part.root.text
                        for part in resp.parts
                        if isinstance(part.root, TextPart)
                    )

            full_response = ''.join(responses).strip()
            logger.info('Test Result: %s', full_response)

            if all(token in full_response for token in expected_end_tokens):
                logger.info('--- INTEGRATION TEST PASSED ---')
            else:
                logger.error(
                    '--- INTEGRATION TEST FAILED: Some verification tokens missing ---'
                )
                for sdk, agent_proc in zip(
                    tested_sdks, agent_procs, strict=True
                ):
                    log_process_output(agent_proc, sdk)
                sys.exit(1)

    except Exception:
        logger.exception('Integration test aborted due to error.')
        # Attempt to log process outputs
        for sdk, agent_proc in zip(tested_sdks, agent_procs, strict=True):
            log_process_output(agent_proc, sdk)
        sys.exit(1)
    finally:
        logger.info('Decommissioning agents...')
        for proc in agent_procs:
            proc.terminate()
        _clean_ports(*ports)


@click.command()
@click.option('--sdks', default='python_v03,go_v03')
@click.option('--traversal', default='euler')
def main(sdks: str, traversal: str) -> None:
    """Execute the multi-agent integration test traversal."""
    asyncio.run(main_async(sdks, traversal))


if __name__ == '__main__':
    main()
