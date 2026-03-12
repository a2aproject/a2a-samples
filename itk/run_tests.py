import asyncio
import json
import logging
import sys

import httpx

from testlib import _clean_ports, execute_itk_test, start_itk_cluster


logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Hardcoded test case definitions
TEST_CASES = [
    {
        'name': 'v03-core',
        'sdks': ['python_v03', 'go_v03'],
        'traversal': 'euler',
        'edges': None,
        'protocols': ['jsonrpc', 'grpc'],
    },
    {
        'name': 'python-v03-v10-all-transports',
        'sdks': ['python_v03', 'python_v10'],
        'protocols': ['jsonrpc', 'grpc', 'http_json'],
        'traversal': 'euler',
        'edges': None,
    },
    {
        'name': 'python-v03-go-v03-python-v10-hub-all-common-transports',
        'sdks': ['python_v03', 'go_v03', 'python_v10'],
        'protocols': ['jsonrpc', 'grpc'],
        'traversal': 'euler',
        'edges': ['2->0', '2->1', '0->2', '1->2'],
    },
    {
        'name': 'full-backwards-compat-with-jsonrpc',
        'sdks': ['python_v03', 'go_v03', 'python_v10', 'go_v10_v03_compat'],
        'protocols': ['jsonrpc'],
        'traversal': 'euler',
        'edges': ['3->0', '3->1', '2->0', '2->1', '0->2', '0->3', '1->2', '1->3'],
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
    procs, uris, ports = await start_itk_cluster(sdk_list)

    # 3. Retrieve and print API schema from the first agent

    try:
        # 3. Define the test tasks
        tasks = [
            execute_itk_test(
                sdks=case['sdks'],
                traversal=case['traversal'],
                edges=case['edges'],
                scenario_name=case['name'],
                protocols=case.get('protocols'),
            )
            for case in TEST_CASES
        ]

        # 4. Run all scenarios concurrently against the shared cluster
        logger.info('Starting concurrent scenario execution...')
        await asyncio.gather(*tasks)

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
