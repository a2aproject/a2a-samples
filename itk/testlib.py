import asyncio  # noqa: I001
import base64
import logging
import subprocess
import time
import uuid
import os

import httpx

import test_suite


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





async def _check_agent_ready(
    name: str, url: str, timeout_seconds: int = 35
) -> bool:
    """Verify agent readiness by attempting to fetch the agent card.

    Args:
        name: Name of the agent.
        url: The URL pointing to the agent's JSON-RPC endpoint.
        timeout_seconds: Duration in seconds to wait for readiness. Defaults to 35.

    Returns:
        bool: True if card fetched successfully within the timeout, otherwise False.
    """
    start = time.time()
    base_url = url.rstrip('/')
    if not base_url.endswith('/jsonrpc'):
        target_url = f"{base_url}/jsonrpc/.well-known/agent-card.json"
    else:
        target_url = f"{base_url}/.well-known/agent-card.json"

    async with httpx.AsyncClient(timeout=5) as http_client:
        while time.time() - start < timeout_seconds:
            try:
                response = await http_client.get(target_url)
                if response.status_code == 200:
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


def _create_payload(is_v0: bool, test_instruction: instruction_pb2.Instruction) -> dict:
    """Creates the JSON-RPC payload for the test instruction."""
    inst_bytes = test_instruction.SerializeToString()
    b64_inst = base64.b64encode(inst_bytes).decode('utf-8')
    
    if is_v0:
        method = 'message/send'
        params = {
            "message": {
                "role": "user",
                "messageId": str(uuid.uuid4()),
                "parts": [
                    {
                        "kind": "file",
                        "file": {
                            "bytes": b64_inst,
                            "mimeType": "application/x-protobuf",
                            "name": "instruction.bin"
                        }
                    }
                ],
                "metadata": {"a2a/protocol_version": "0.3"}
            }
        }
    else:
        method = 'SendMessage'
        params = {
            "message": {
                "role": "ROLE_USER",
                "messageId": str(uuid.uuid4()),
                "parts": [
                    {
                        "raw": b64_inst,
                        "mediaType": "application/x-protobuf",
                        "filename": "instruction.bin"
                    }
                ]
            }
        }

    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": str(uuid.uuid4())
    }


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
    first_sdk = sdks[0]
    is_v0 = 'v03' in first_sdk
    
    target_url = test_suite.get_agent_card_uri(first_sdk)
    is_go_env = os.path.exists('/app/agents/repo/itk/go.mod')
    if 'go' in first_sdk or (first_sdk == 'current' and is_go_env):
        target_url = target_url.rstrip('/')
    else:
        target_url = target_url.rstrip('/') + '/'
    
    json_rpc_request = _create_payload(is_v0, test_instruction)

    responses = []
    logger.info(
        'Dispatching %s payload to %s via JSON-RPC (%s)...',
        label,
        target_url,
        "v0" if is_v0 else "v1"
    )
    
    headers = {}
    if is_v0:
        headers['A2A-Version'] = '0.3'
    else:
        headers['A2A-Version'] = '1.0'
        
    async with httpx.AsyncClient(timeout=120) as http_client:
        response = await http_client.post(target_url, json=json_rpc_request, headers=headers)
        response.raise_for_status()
        response_json = response.json()
        
        logger.info('!!!!!!!!!!!!Received response: %s!!!!!!!!!!!!!', response_json)
        
        if 'error' in response_json:
            raise RuntimeError(f"JSON-RPC Error: {response_json['error']}")
            
        result = response_json.get('result', {})
        
        message_data = None
        if 'message' in result:
            message_data = result['message']
        elif 'status' in result and 'message' in result['status']:
            message_data = result['status']['message']
        elif 'task' in result and 'status' in result['task'] and 'message' in result['task']['status']:
            message_data = result['task']['status']['message']
                
        if message_data and 'parts' in message_data:
            for part in message_data['parts']:
                if 'text' in part and part['text']:
                    responses.append(part['text'])

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
