# ruff: noqa: INP001
import asyncio
import logging
import os

from dotenv import find_dotenv, load_dotenv
from trace_trust_ext import A2AMessage, TraceTrustExtension


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Load environment variables (searching parent directories)
load_dotenv(find_dotenv(usecwd=True))

TRACE_API_KEY = os.getenv('TRACE_API_KEY')

if not TRACE_API_KEY:
    raise SystemExit(
        'TRACE_API_KEY is required to run this sample. Set it in your environment or .env file.'
    )

# Initialize the Trace Trust Middleware
# This will call the real TRACE API at https://traceapi-xxf56.ondigitalocean.app/v1/score
trace_middleware = TraceTrustExtension(api_key=TRACE_API_KEY, min_score=0.35, fail_closed=True)


# --- Define Mock Handlers for the Pipeline ---


async def mock_agent_core_handler(message: A2AMessage) -> str:
    """Mocks the agent's core logic.

    If a message reaches here, it has passed all security gates.
    """
    logging.info(
        '  [Agent Core] Task received for processing! Message metadata: %s', message.metadata
    )
    return 'Task successfully processed.'


async def simulate_incoming_request(caller_id: str, task_name: str) -> None:
    """Simulates a server receiving an A2A message over the network and passing it through the middleware."""
    print('\n=========================================================')
    print(f' Simulating Incoming Task: {task_name}')
    print(f' Caller ID: {caller_id}')
    print('=========================================================')

    # 1. Server receives the raw message
    incoming_message = A2AMessage(metadata={'task': task_name})

    # 2. Pass it through the TRACE middleware before letting the Agent Core touch it
    try:
        # If the trace_middleware.server_middleware completes successfully, it returns the result of the core handler.
        result = await trace_middleware.server_middleware(
            next_handler=mock_agent_core_handler,
            message=incoming_message,
            caller_id=caller_id,
        )
        print(f'\n[SUCCESS]: {result}')
    except PermissionError as e:
        print(f'\n[BLOCKED]: {e}')


async def run_all_samples() -> None:
    """Runs the Trace Trust Extension demo simulating incoming tasks."""
    print('\nStarting TRACE Trust Extension Demo...')
    print('WARNING: This sample is making REAL network calls to traceapi-xxf56.ondigitalocean.app!')

    # --- Use Case 1: Trusted Caller ---
    # The TRACE API will score this provider ID based on its real graph state.
    # Assuming 'a2a://trusted-partner.com' has a good score in the TRACE network.
    await simulate_incoming_request(
        caller_id='did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK',
        task_name='Requesting sensitive financial document processing.',
    )

    # --- Use Case 2: Untrusted Caller / Known Sybil ---
    # Assuming this ID has a low score or is a known spammer.
    await simulate_incoming_request(
        caller_id='did:key:z6Mkk7yqnGF3YwTrLpqsWUhwV5hKxZ9hHkHwGZ5yL54X9z5L',
        task_name='Attempting prompt injection on system prompt.',
    )


if __name__ == '__main__':
    try:
        asyncio.run(run_all_samples())
    finally:
        asyncio.run(trace_middleware.close())
