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
        'name': 'resubscribe-jsonrpc',
        'sdks': ['python_v10', 'go_v03'],
        'protocols': ['jsonrpc'],
        'edges': None,
        'streaming': True,
        'behavior': 'resubscribe',
    },
     {
        'name': 'resubscribe-grpc',
        'sdks': ['python_v03', 'python_v10', 'go_v03'],
        'protocols': ['grpc'],
        'edges': None,
        'streaming': True,
        'behavior': 'resubscribe',
    },
    {
        'name': 'resubscribe-python-all-protocols',
        'sdks': ['python_v03', 'python_v10'],
        'protocols': ['jsonrpc', 'grpc', 'http_json'],
        'edges': None,
        'streaming': True,
        'behavior': 'resubscribe',
    },
    {
        'name': 'resubscribe-v10-all-protocols',
        'sdks': ['python_v10', 'go_v10'],
        'protocols': ['jsonrpc', 'grpc', 'http_json'],
        'edges': None,
        'streaming': True,
        'behavior': 'resubscribe',
    },
    {
        'name': 'resubscribe-v03-grpc',
        'sdks': ['python_v03', 'go_v03'],
        'protocols': ['grpc'],
        'edges': None,
        'streaming': True,
        'behavior': 'resubscribe',
    },
    {
        'name': 'go-v03-v10-push-notification',
        'sdks': ['go_v03', 'go_v10'],
        'protocols': ['jsonrpc'],
        'edges': None,
        'behavior': 'push_notification',
    },
    {
        'name': 'python-v10-and-v03-sdks-push-notifications',
        'sdks': ['python_v10', 'python_v03', 'go_v03'],
        'protocols': ['jsonrpc'],
        'edges': None,
        'behavior': 'push_notification',
    },
    {
        'name': 'python-v10-and-v03-sdks-push-notifications-grpc-http-json',
        'sdks': ['python_v10', 'python_v03'],
        'protocols': ['grpc', 'http_json'],
        'edges': None,
        'behavior': 'push_notification',
    },
    {
        'name': 'v03-core',
        'sdks': ['python_v03', 'go_v03'],
        'edges': None,
        'protocols': ['jsonrpc', 'grpc'],
        'behavior': 'send_message',
    },
    {
        'name': 'v03-core-streaming',
        'sdks': ['python_v03', 'go_v03'],
        'edges': None,
        'protocols': ['jsonrpc', 'grpc'],
        'streaming': True,
        'behavior': 'send_message',
    },
    {
        'name': 'v10-core',
        'sdks': ['python_v10', 'go_v10'],
        'protocols': ['http_json', 'jsonrpc', 'grpc'],
        'edges': None,
        'behavior': 'send_message',
    },
    {
        'name': 'v10-core-streaming',
        'sdks': ['python_v10', 'go_v10'],
        'protocols': ['jsonrpc', 'grpc', 'http_json'],
        'edges': None,
        'streaming': True,
        'behavior': 'send_message',
    },
    {
        'name': 'python-v03-v10-all-transports',
        'sdks': ['python_v03', 'python_v10'],
        'protocols': ['jsonrpc', 'grpc', 'http_json'],
        'edges': None,
        'behavior': 'send_message',
    },
    {
        'name': 'python-v03-v10-all-transports-streaming',
        'sdks': ['python_v03', 'python_v10'],
        'protocols': ['jsonrpc', 'grpc', 'http_json'],
        'edges': None,
        'streaming': True,
        'behavior': 'send_message',
    },
    {
        'name': 'python-v03-go-v03-python-v10-hub-all-common-transports',
        'sdks': ['python_v03', 'go_v03', 'python_v10'],
        'protocols': ['jsonrpc', 'grpc'],
        'edges': ['2->0', '2->1', '0->2', '1->2'],
        'behavior': 'send_message',
        'build_subtests': True,
    },
    {
        'name': 'python-v03-go-v03-python-v10-hub-all-common-transports-streaming',
        'sdks': ['python_v03', 'go_v03', 'python_v10'],
        'protocols': ['jsonrpc', 'grpc'],
        'edges': ['2->0', '2->1', '0->2', '1->2'],
        'streaming': True,
        'behavior': 'send_message',
    },
    {
        'name': 'full-backwards-compat-with-jsonrpc',
        'sdks': ['python_v03', 'go_v03', 'python_v10', 'go_v10'],
        'protocols': ['jsonrpc'],
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
        'edges': ['1->3', '3->1', '2->0', '0->2'],
        'behavior': 'send_message',
    },
    {
        'name': 'failing-go-v03-http-json',
        'sdks': ['python_v03', 'python_v10', 'go_v03'],
        'protocols': ['http_json'],
        'edges': None,
        'behavior': 'send_message',
    },
    {
        'name': 'failing-go-v10-grpc',
        'sdks': ['go_v03', 'go_v10'],
        'protocols': ['grpc'],
        'edges': None,
        'behavior': 'send_message',
    },
    {
        'name': 'failing-python-v10-go-v10-push-notifications',
        'sdks': ['python_v10', 'go_v10'],
        'protocols': ['jsonrpc'],
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
        # 3. Run all scenarios sequentially to prevent overwhelming the shared cluster
        logger.info('Starting sequential scenario execution...')
        results = []
        for case in TEST_CASES:
            logger.info("Executing parent scenario '%s'...", case['name'])
            res_dict = await execute_itk_test(
                sdks=case['sdks'],
                behavior=case['behavior'],
                edges=case['edges'],
                scenario_name=case['name'],
                protocols=case.get('protocols'),
                streaming=case.get('streaming', False),
                build_subtests=case.get('build_subtests', False),
            )
            results.append(res_dict)

        # Merge the results dictionaries
        merged_results = {}
        for res_dict in results:
            merged_results.update(res_dict)

        # 5. Report results
        all_passed = True
        for idx, (name, details) in enumerate(merged_results.items()):
            passed = details['passed']
            status = 'PASSED' if passed else 'FAILED'
            logger.info(
                "Scenario %s/%s '%s': %s",
                idx + 1,
                len(merged_results),
                name,
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
