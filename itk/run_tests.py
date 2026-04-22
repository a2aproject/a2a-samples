import asyncio
import logging
import os
import subprocess
import sys

import httpx
from testlib import (
    _clean_ports,
    execute_itk_test,
    start_itk_cluster,
    start_notification_server,
)


logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Hardcoded test case definitions
TEST_CASES = [
    {
        'name': 'go-v03-v10-push-notification',
        'sdks': ['go_v03', 'go_v10'],
        'protocols': ['jsonrpc'],
        'traversal': 'euler',
        'edges': None,
        'behavior': 'push_notification',
    },
    {
        'name': 'python-v10-and-v03-sdks-push-notifications',
        'sdks': ['python_v10', 'python_v03', 'go_v03'],
        'protocols': ['jsonrpc'],
        'traversal': 'euler',
        'edges': None,
        'behavior': 'push_notification',
    },
    {
        'name': 'python-v10-and-v03-sdks-push-notifications-grpc-http-json',
        'sdks': ['python_v10', 'python_v03'],
        'protocols': ['grpc', 'http_json'],
        'traversal': 'euler',
        'edges': None,
        'behavior': 'push_notification',
    },
    {
        'name': 'v03-core',
        'sdks': ['python_v03', 'go_v03'],
        'traversal': 'euler',
        'edges': None,
        'protocols': ['jsonrpc', 'grpc'],
        'behavior': 'send_message',
    },
    {
        'name': 'v03-core-streaming',
        'sdks': ['python_v03', 'go_v03'],
        'traversal': 'euler',
        'edges': None,
        'protocols': ['jsonrpc', 'grpc'],
        'streaming': True,
        'behavior': 'send_message',
    },
    {
        'name': 'v10-core',
        'sdks': ['python_v10', 'go_v10'],
        'protocols': ['http_json', 'jsonrpc', 'grpc'],
        'traversal': 'euler',
        'edges': None,
        'behavior': 'send_message',
    },
    {
        'name': 'v10-core-streaming',
        'sdks': ['python_v10', 'go_v10'],
        'protocols': ['jsonrpc', 'grpc', 'http_json'],
        'traversal': 'euler',
        'edges': None,
        'streaming': True,
        'behavior': 'send_message',
    },
    {
        'name': 'python-v03-v10-all-transports',
        'sdks': ['python_v03', 'python_v10'],
        'protocols': ['jsonrpc', 'grpc', 'http_json'],
        'traversal': 'euler',
        'edges': None,
        'behavior': 'send_message',
    },
    {
        'name': 'python-v03-v10-all-transports-streaming',
        'sdks': ['python_v03', 'python_v10'],
        'protocols': ['jsonrpc', 'grpc', 'http_json'],
        'traversal': 'euler',
        'edges': None,
        'streaming': True,
        'behavior': 'send_message',
    },
    {
        'name': 'python-v03-go-v03-python-v10-hub-all-common-transports',
        'sdks': ['python_v03', 'go_v03', 'python_v10'],
        'protocols': ['jsonrpc', 'grpc'],
        'traversal': 'euler',
        'edges': ['2->0', '2->1', '0->2', '1->2'],
        'behavior': 'send_message',
    },
    {
        'name': 'python-v03-go-v03-python-v10-hub-all-common-transports-streaming',
        'sdks': ['python_v03', 'go_v03', 'python_v10'],
        'protocols': ['jsonrpc', 'grpc'],
        'traversal': 'euler',
        'edges': ['2->0', '2->1', '0->2', '1->2'],
        'streaming': True,
        'behavior': 'send_message',
    },
    {
        'name': 'full-backwards-compat-with-jsonrpc',
        'sdks': ['python_v03', 'go_v03', 'python_v10', 'go_v10'],
        'protocols': ['jsonrpc'],
        'traversal': 'euler',
        'edges': [
            '3->0',
            '3->1',
            '2->0',
            '2->1',
            '0->2',
            '0->3',
            '1->2',
            '1->3',
        ],
        'behavior': 'send_message',
    },
    {
        'name': 'full-backwards-compat-with-jsonrpc-streaming',
        'sdks': ['python_v03', 'go_v03', 'python_v10', 'go_v10'],
        'protocols': ['jsonrpc'],
        'traversal': 'euler',
        'edges': [
            '3->0',
            '3->1',
            '2->0',
            '2->1',
            '0->2',
            '0->3',
            '1->2',
            '1->3',
        ],
        'streaming': True,
        'behavior': 'send_message',
    },
    {
        'name': 'disconnected-components',
        'sdks': ['python_v03', 'go_v03', 'python_v10', 'go_v10'],
        'protocols': ['jsonrpc'],
        'traversal': 'euler',
        'edges': ['1->3', '3->1', '2->0', '0->2'],
        'behavior': 'send_message',
    },
    {
        'name': 'failing-go-v03-http-json',
        'sdks': ['python_v03', 'python_v10', 'go_v03'],
        'protocols': ['http_json'],
        'traversal': 'euler',
        'edges': None,
        'behavior': 'send_message',
    },
    {
        'name': 'failing-go-v10-grpc',
        'sdks': ['go_v03', 'go_v10'],
        'protocols': ['grpc'],
        'traversal': 'euler',
        'edges': None,
        'behavior': 'send_message',
    },
    {
        'name': 'failing-python-v10-go-v10-push-notifications',
        'sdks': ['python_v10', 'go_v10'],
        'protocols': ['jsonrpc'],
        'traversal': 'euler',
        'edges': ['0->1', '1->0'],
        'behavior': 'push_notification',
    },
]


async def main_async() -> None:
    """Execute hardcoded integration test scenarios concurrently."""
    # 1. Identify all unique SDKs needed across all test cases
    all_required_sdks = set()
    for case in TEST_CASES:
        all_required_sdks.update(case['sdks'])

    # Convert to sorted list for deterministic port assignment
    # (Though AGENT_DEFS currently have static ports anyway)
    sdk_list = sorted(all_required_sdks)

    # 2. Start the shared cluster
    procs, _uris, ports = await start_itk_cluster(sdk_list)

    try:
        # 3. Define the test tasks
        tasks = [
            execute_itk_test(
                sdks=case['sdks'],
                traversal=case['traversal'],
                behavior=case['behavior'],
                edges=case['edges'],
                scenario_name=case['name'],
                protocols=case.get('protocols'),
                streaming=case.get('streaming', False),
                notification_server_url=case.get('notification_server_url'),
            )
            for case in TEST_CASES
        ]

        # 4. Run all scenarios concurrently against the shared cluster
        logger.info('Starting concurrent scenario execution...')
        results = await asyncio.gather(*tasks)

        # 5. Report results
        all_passed = True
        for idx, (case, passed) in enumerate(
            zip(TEST_CASES, results, strict=True)
        ):
            status = 'PASSED' if passed else 'FAILED'
            logger.info(
                "Scenario %s/%s '%s': %s",
                idx + 1,
                len(TEST_CASES),
                case['name'],
                status,
            )
            if not passed:
                all_passed = False

        if not all_passed:
            logger.error('One or more test scenarios failed.')
        else:
            logger.info('All test scenarios passed.')

    except Exception:
        logger.exception('Concurrent test execution encountered an error.')
        sys.exit(1)
    finally:
        logger.info('Decommissioning shared agent cluster...')
        for proc in procs:
            proc.terminate()
        _clean_ports(*ports)


def main() -> None:
    """Entry point for the integration test orchestrator."""
    asyncio.run(main_async())


if __name__ == '__main__':
    main()
