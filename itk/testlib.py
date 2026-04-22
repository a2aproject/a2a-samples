import asyncio  # noqa: I001
import base64
import logging
import socket
import subprocess
import time
import uuid
import os

import httpx

import test_suite


from agents.python.v03.pyproto import instruction_pb2


logger = logging.getLogger(__name__)


def _get_free_port() -> int:
    """Finds an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


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
        target_url = f'{base_url}/jsonrpc/.well-known/agent-card.json'
    else:
        target_url = f'{base_url}/.well-known/agent-card.json'

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


async def start_notification_server(
    port: int, test_name: str
) -> subprocess.Popen:
    """Starts the mock notification server and waits for readiness."""
    _clean_ports(port)
    logger.info('Starting notification server on port %s...', port)

    cwd = os.path.dirname(os.path.abspath(__file__))

    log_level = os.environ.get('ITK_LOG_LEVEL', 'INFO').upper()
    stdout_target = subprocess.PIPE
    stderr_target = subprocess.PIPE

    if log_level == 'DEBUG':
        logs_dir = os.path.join(cwd, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, f'{test_name}_notifications.log')
        stdout_target = open(log_file, 'w')
        stderr_target = subprocess.STDOUT
        logger.info('Notification server logging to %s', log_file)

    proc = subprocess.Popen(
        [
            'uv',
            'run',
            'uvicorn',
            'notifications_app:create_notifications_app',
            '--factory',
            '--host',
            '127.0.0.1',
            '--port',
            str(port),
        ],
        cwd=cwd,
        stdout=stdout_target,
        stderr=stderr_target,
        text=True,
    )

    url = f'http://127.0.0.1:{port}'
    async with httpx.AsyncClient() as client:
        for _ in range(10):
            try:
                resp = await client.get(f'{url}/health')
                if resp.status_code == 200:
                    logger.info('Notification server is ready.')
                    break
            except Exception:
                await asyncio.sleep(0.5)
        else:
            proc.terminate()
            stdout, stderr = proc.communicate()
            logger.error(
                'Notification server failed to start. Stdout:\n%s\nStderr:\n%s',
                stdout,
                stderr,
            )
            raise RuntimeError('Notification server failed to start.')

    return proc


def _create_payload(
    is_v0: bool, test_instruction: instruction_pb2.Instruction
) -> dict:
    """Creates the JSON-RPC payload for the test instruction."""
    inst_bytes = test_instruction.SerializeToString()
    b64_inst = base64.b64encode(inst_bytes).decode('utf-8')

    if is_v0:
        method = 'message/send'
        params = {
            'message': {
                'role': 'user',
                'messageId': str(uuid.uuid4()),
                'parts': [
                    {
                        'kind': 'file',
                        'file': {
                            'bytes': b64_inst,
                            'mimeType': 'application/x-protobuf',
                            'name': 'instruction.bin',
                        },
                    }
                ],
                'metadata': {'a2a/protocol_version': '0.3'},
            }
        }
    else:
        method = 'SendMessage'
        params = {
            'message': {
                'role': 'ROLE_USER',
                'messageId': str(uuid.uuid4()),
                'parts': [
                    {
                        'raw': b64_inst,
                        'mediaType': 'application/x-protobuf',
                        'filename': 'instruction.bin',
                    }
                ],
            }
        }

    return {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': str(uuid.uuid4()),
    }


def _extract_response_text(result: dict) -> str:
    """Extracts the response text from the JSON-RPC result."""
    responses = []
    message_data = None
    if 'message' in result:
        message_data = result['message']
    elif 'status' in result and 'message' in result['status']:
        message_data = result['status']['message']
    elif (
        'task' in result
        and 'status' in result['task']
        and 'message' in result['task']['status']
    ):
        message_data = result['task']['status']['message']

    if message_data and 'parts' in message_data:
        for part in message_data['parts']:
            if 'text' in part and part['text']:
                responses.append(part['text'])

    return ''.join(responses).strip()


def _extract_text_from_parts(message_data: dict) -> list[str]:
    texts = []
    if 'parts' in message_data:
        for part in message_data['parts']:
            if 'text' in part and part['text']:
                texts.append(part['text'])
    return texts


def _read_v10_notif(event: dict) -> list[str]:
    # v1.0 notifications with agent messages should be in 'statusUpdate'
    update = event.get('statusUpdate') or event.get('status_update')
    if update and isinstance(update, dict) and 'status' in update:
        status = update['status']
        if isinstance(status, dict) and 'message' in status:
            message_data = status['message']
            if message_data and message_data.get('role') == 'ROLE_AGENT':
                return _extract_text_from_parts(message_data)
    return []


def _read_v03_notif(event: dict) -> list[str]:
    # v0.3 notifications have flat structure, agent messages in 'status.message'
    status_obj = event.get('status')
    if status_obj and isinstance(status_obj, dict) and 'message' in status_obj:
        message_data = status_obj['message']
        if message_data and message_data.get('role') == 'agent':
            return _extract_text_from_parts(message_data)
    return []


async def read_push_notifications(
    notification_server_url: str,
) -> list[str]:
    """Reads all push notifications from the mock notification server."""
    url = f'{notification_server_url}/notifications'
    responses = []

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                notifications = data.get('notifications', [])
                for notif in notifications:
                    event = notif.get('event', {})
                    texts = _read_v10_notif(event)
                    if not texts:
                        texts = _read_v03_notif(event)
                    responses.extend(texts)
        except Exception as e:
            logger.debug('Error reading notifications: %s', e)

    return responses


def _verify_send_message(
    result: dict,
    expected_end_tokens: list[str],
    label: str,
) -> bool:
    full_response = _extract_response_text(result)

    logger.info('Test Result for %s: %s', label, full_response)

    if all(token in full_response for token in expected_end_tokens):
        logger.info('--- INTEGRATION TEST PASSED: %s ---', label)
        return True

    logger.error(
        '--- INTEGRATION TEST FAILED: Verification tokens missing for %s ---',
        label,
    )
    return False


async def _verify_push_notification(
    notification_texts: list[str],
    expected_end_tokens: list[str],
    protocols: list[str],
    label: str,
) -> bool:
    full_response = ''.join(notification_texts)

    # Verify intermediate states to ensure every hop pushed
    # Split expected_end_tokens into chains by terminal token
    chains = []
    current_chain = []
    for token in expected_end_tokens:
        current_chain.append(token)
        if token.startswith('traversal-completed:'):
            chains.append(current_chain)
            current_chain = []
    if current_chain:
        chains.append(current_chain)

    expected_states = []
    for chain in chains:
        if not chain:
            continue
        terminal_token = chain[-1]
        expected_states.append(terminal_token)
        current_state = terminal_token
        for token in chain[:-1]:
            current_state = f'{token}\n{current_state}'
            expected_states.append(current_state)

    logger.info('Expected intermediate states: %s', expected_states)

    remaining_states = list(expected_states)
    for text in notification_texts:
        for state in list(remaining_states):
            if state in text:
                remaining_states.remove(state)

    if remaining_states:
        logger.error(
            '--- INTEGRATION TEST FAILED: Missing intermediate states: %s ---',
            remaining_states,
        )
        return False

    logger.info('Test Result for %s: %s', label, full_response)

    if all(token in full_response for token in expected_end_tokens):
        logger.info('--- INTEGRATION TEST PASSED: %s ---', label)
        return True

    logger.error(
        '--- INTEGRATION TEST FAILED: Verification tokens missing for %s ---',
        label,
    )
    return False


async def execute_itk_test(  # noqa: PLR0913
    sdks: list[str],
    traversal: str,
    behavior: str,
    edges: list[str] | None = None,
    scenario_name: str | None = None,
    protocols: list[str] | None = None,
    streaming: bool = False,
    notification_server_url: str | None = None,
) -> bool:
    """Executes a traversal test against an ALREADY RUNNING cluster.

    Args:
        sdks: List of SDK identifiers to include in the test.
        traversal: Name of the graph traversal algorithm.
        edges: Optional custom edges.
        scenario_name: Optional label for logging.
        protocols: Optional list of protocols to test.
        streaming: Whether to use streaming.
        behavior: The behavior to test ('send_message' or 'push_notification').
        notification_server_url: URL of the notification server (required for push_notification).
    """
    label = scenario_name or traversal

    notif_server_process = None
    notif_port = None
    if behavior == 'push_notification':
        notif_port = _get_free_port()
        notification_server_url = f'http://127.0.0.1:{notif_port}'
        notif_server_process = await start_notification_server(
            notif_port, label
        )
        logger.info(
            'Started dedicated notification server on port %s for test %s',
            notif_port,
            label,
        )
    test_result = False
    try:
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
            behavior=behavior,
            notification_server_url=notification_server_url,
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

        test_token = str(uuid.uuid4())

        if behavior == 'push_notification' and notification_server_url:
            config = {
                'url': f'{notification_server_url}/notifications',
                'token': test_token,
            }
            logger.info(
                'SETTING CONFIG: is_v0=%s, first_sdk=%s', is_v0, first_sdk
            )
            if is_v0:
                json_rpc_request['params']['configuration'] = {
                    'pushNotificationConfig': config
                }
            else:
                json_rpc_request['params']['configuration'] = {
                    'taskPushNotificationConfig': config
                }
            logger.info(
                'PAYLOAD CONFIG: %s',
                json_rpc_request['params']['configuration'],
            )

        headers = {}
        if is_v0:
            headers['A2A-Version'] = '0.3'
        else:
            headers['A2A-Version'] = '1.0'

        async with httpx.AsyncClient(timeout=120) as http_client:
            response = await http_client.post(
                target_url, json=json_rpc_request, headers=headers
            )
            response.raise_for_status()
            response_json = response.json()

            logger.info(
                '!!!!!!!!!!!!Received response: %s!!!!!!!!!!!!!', response_json
            )

            if 'error' in response_json:
                raise RuntimeError(f'JSON-RPC Error: {response_json["error"]}')

            result = response_json.get('result', {})

            full_response = ''

            if behavior == 'push_notification':
                notification_texts = await read_push_notifications(
                    notification_server_url
                )
                test_result = await _verify_push_notification(
                    notification_texts, expected_end_tokens, protocols, label
                )
            elif behavior == 'send_message':
                test_result = _verify_send_message(
                    result, expected_end_tokens, label
                )
            else:
                raise ValueError(f'Unsupported behavior: {behavior}')
    finally:
        if notif_server_process and notif_port:
            logger.info('Stopping notification server for test %s', label)
            _clean_ports(notif_port)

    return test_result


async def run_itk_test(
    sdks: list[str],
    traversal: str,
    behavior: str,
    edges: list[str] | None = None,
    scenario_name: str | None = None,
) -> bool:
    """Executes a multi-agent integration test traversal.

    Args:
        sdks: List of SDK identifiers to include in the test cluster.
        traversal: Name of the graph traversal algorithm to use.
        behavior: The behavior to test ('send_message' or 'push_notification').
        edges: Optional list of custom graph edges (e.g., "0->1").
        scenario_name: Optional human-readable name for logging.

    Raises:
        RuntimeError: If an agent fails to start or the test verification fails.
    """
    procs, _, ports = await start_itk_cluster(sdks)
    try:
        return await execute_itk_test(
            sdks=sdks,
            traversal=traversal,
            behavior=behavior,
            edges=edges,
            scenario_name=scenario_name,
        )
    finally:
        logger.info(
            'Decommissioning agents for %s...', scenario_name or traversal
        )
        for proc in procs:
            proc.terminate()
        _clean_ports(*ports)
