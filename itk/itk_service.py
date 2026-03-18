import asyncio  # noqa: I001
import logging

import uvicorn

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from testlib import _clean_ports, execute_itk_test, start_itk_cluster


# Configure logging to match run_tests.py style
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title='ITK Test Orchestration Service')
_execution_lock = asyncio.Lock()


class TestCase(BaseModel):
    """Component representing a single test case for ITK."""

    name: str
    sdks: list[str]
    traversal: str
    edges: list[str] | None = None
    protocols: list[str] | None = None
    streaming: bool = False


class RunTestsRequest(BaseModel):
    """Request model for the /run endpoint."""

    tests: list[TestCase]


class RunTestsResponse(BaseModel):
    """Response model for the /run endpoint."""

    results: dict[str, bool]
    all_passed: bool


@app.post('/run', response_model=RunTestsResponse)
async def run_tests(request: RunTestsRequest) -> RunTestsResponse:
    """FastAPI endpoint to execute ITK tests with concurrency control."""
    # We allow only single collection of test cases to be executed at a time
    # to avoid wipeing out the ports that are utilized at the moment.
    async with _execution_lock:
        try:
            response = await _test(request)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception('Concurrent test execution encountered an error.')
            raise HTTPException(
                status_code=500, detail=f'Execution error: {e!s}'
            ) from e
    return response


async def _test(request: RunTestsRequest) -> RunTestsResponse:
    """Internal logic to execute a batch of ITK test scenarios."""
    if not request.tests:
        raise HTTPException(status_code=400, detail='No tests provided')

    # 1. Identify all unique SDKs needed across all test cases
    all_required_sdks = set()
    for case in request.tests:
        all_required_sdks.update(case.sdks)

    sdk_list = sorted(all_required_sdks)

    logger.info(
        'Starting test execution for %d scenarios using SDKs: %s',
        len(request.tests),
        sdk_list,
    )

    # 2. Start the shared cluster
    try:
        procs, _uris, ports = await start_itk_cluster(sdk_list)
    except Exception as e:
        logger.exception('Failed to start ITK cluster')
        raise HTTPException(
            status_code=500, detail=f'Failed to start ITK cluster: {e!s}'
        ) from e

    try:
        # 3. Define the test tasks
        tasks = [
            execute_itk_test(
                sdks=case.sdks,
                traversal=case.traversal,
                edges=case.edges,
                scenario_name=case.name,
                protocols=case.protocols,
                streaming=case.streaming,
            )
            for case in request.tests
        ]

        # 4. Run all scenarios concurrently against the shared cluster
        logger.info('Starting concurrent scenario execution...')
        results_list = await asyncio.gather(*tasks)

        # 5. Prepare results
        results_map = {}
        all_passed = True
        for case, passed in zip(request.tests, results_list, strict=True):
            results_map[case.name] = passed
            if not passed:
                all_passed = False

            status = 'PASSED' if passed else 'FAILED'
            logger.info("Scenario '%s': %s", case.name, status)

        return RunTestsResponse(results=results_map, all_passed=all_passed)

    except Exception as e:
        logger.exception('Concurrent test execution encountered an error.')
        raise HTTPException(
            status_code=500, detail=f'Execution error: {e!s}'
        ) from e
    finally:
        logger.info('Decommissioning shared agent cluster...')
        for proc in procs:
            proc.terminate()
        _clean_ports(*ports)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)  # noqa: S104
