"""Validates all three AI Design Blueprint governance principles via A2A.

Run with the agent server already started:
    uv run python __main__.py &
    uv run python test_client.py

Three assertions:
    1. Approval gate  — send delete request, assert task reaches input-required state.
    2. Mid-task steer — reply with anything other than 'confirm', assert canceled.
    3. Streaming + confirm — reply 'confirm', assert completed (with working events).
"""

import asyncio
import json
import sys

from uuid import uuid4

import httpx


AGENT_URL = 'http://127.0.0.1:9999'
TIMEOUT = 15.0
A2A_HEADERS = {'A2A-Version': '1.0'}


def _msg_params(
    text: str,
    context_id: str | None = None,
    task_id: str | None = None,
) -> dict:
    msg: dict = {
        'messageId': str(uuid4()),
        'role': 'ROLE_USER',
        'parts': [{'text': text}],
    }
    if context_id:
        msg['contextId'] = context_id
    if task_id:
        msg['taskId'] = task_id
    return {'message': msg}


async def rpc(method: str, params: dict, client: httpx.AsyncClient) -> dict:
    """Send a JSON-RPC 2.0 request, return the result dict."""
    payload = {
        'jsonrpc': '2.0',
        'id': str(uuid4()),
        'method': method,
        'params': params,
    }
    r = await client.post(
        AGENT_URL, json=payload, headers=A2A_HEADERS, timeout=TIMEOUT
    )
    r.raise_for_status()
    data = r.json()
    if 'error' in data:
        raise AssertionError(f'RPC error: {data["error"]}')
    return data['result']


async def stream_events(params: dict, client: httpx.AsyncClient) -> list[dict]:
    """Send via SendStreamingMessage, collect all SSE events, return as list of dicts."""
    payload = {
        'jsonrpc': '2.0',
        'id': str(uuid4()),
        'method': 'SendStreamingMessage',
        'params': params,
    }
    events: list[dict] = []
    async with client.stream(
        'POST', AGENT_URL, json=payload, headers=A2A_HEADERS, timeout=TIMEOUT
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if line.startswith('data: '):
                raw = line[6:].strip()
                if raw and raw != '[DONE]':
                    events.append(json.loads(raw))
    return events


async def test_approval_gate(client: httpx.AsyncClient) -> tuple[str, str]:
    """
    Principle tested: Explicit approval before destructive action (Blueprint P8).

    Assert: a delete request yields TASK_STATE_INPUT_REQUIRED, not immediate execution.
    """
    print('  [1] Approval gate...', end=' ', flush=True)
    result = await rpc(
        'SendMessage', _msg_params('delete /tmp/test.txt'), client
    )
    task = result['task']
    state = task['status']['state']
    assert state == 'TASK_STATE_INPUT_REQUIRED', (  # noqa: S101
        f'Expected TASK_STATE_INPUT_REQUIRED, got {state!r}. '
        'Agent must pause for approval before destructive action.'
    )
    context_id: str = task['contextId']
    task_id: str = task['id']
    print(f'PASS  (state={state!r}, context_id={context_id[:8]}...)')
    return context_id, task_id


async def test_mid_task_steering(
    context_id: str, task_id: str, client: httpx.AsyncClient
) -> None:
    """
    Principle tested: Mid-task steering — cancellation (Blueprint P7).

    Assert: replying with anything other than 'confirm' cancels the pending task.
    """
    print('  [2] Mid-task steering (cancel)...', end=' ', flush=True)
    result = await rpc(
        'SendMessage', _msg_params('abort', context_id, task_id), client
    )
    task = result['task']
    state = task['status']['state']
    assert state == 'TASK_STATE_CANCELED', (  # noqa: S101
        f'Expected TASK_STATE_CANCELED, got {state!r}. '
        "Agent must honour steering — user said 'abort', not 'confirm'."
    )
    print(f'PASS  (state={state!r})')


async def test_streaming_and_confirm(client: httpx.AsyncClient) -> None:
    """
    Principle tested: Perceptible background work via streaming (Blueprint P5).

    Assert: after confirmation, agent emits intermediate 'working' events
    before reaching 'completed'.
    """
    print('  [3] Streaming + confirm...', end=' ', flush=True)

    # Fresh context — start a new delete request.
    result = await rpc(
        'SendMessage', _msg_params('delete /tmp/demo.txt'), client
    )
    assert result['task']['status']['state'] == 'TASK_STATE_INPUT_REQUIRED', (  # noqa: S101
        'Prerequisite failed: expected TASK_STATE_INPUT_REQUIRED on fresh delete request.'
    )
    context_id: str = result['task']['contextId']
    task_id: str = result['task']['id']

    # Confirm and collect streaming events.
    events = await stream_events(
        _msg_params('confirm', context_id, task_id), client
    )

    def _state(e: dict) -> str:
        r = e.get('result', {})
        # TaskStatusUpdateEvent (streaming): result.statusUpdate.status.state
        if 'statusUpdate' in r:
            return r['statusUpdate'].get('status', {}).get('state', '')
        # Task object (streaming or non-streaming): result.task.status.state
        if 'task' in r:
            return r['task'].get('status', {}).get('state', '')
        return ''

    # Validate we got at least one 'working' event (perceptible progress).
    working_events = [e for e in events if _state(e) == 'TASK_STATE_WORKING']
    assert len(working_events) >= 1, (  # noqa: S101
        f'Expected at least 1 working event, got {len(working_events)}. '
        'Agent must stream intermediate progress — background work must be perceptible.\n'
        f'All event states: {[_state(e) for e in events]}'
    )

    # Validate final state is 'completed'.
    final_events = [e for e in events if _state(e) == 'TASK_STATE_COMPLETED']
    assert len(final_events) >= 1, (  # noqa: S101
        f'Expected TASK_STATE_COMPLETED event. '
        f'All event states: {[_state(e) for e in events]}'
    )

    print(
        f'PASS  ({len(working_events)} working event(s) → completed, '
        f'{len(events)} total events)'
    )


async def main() -> None:
    print('\nAI Design Blueprint — A2A governance validation\n')
    print('Connecting to agent at', AGENT_URL, '...')

    async with httpx.AsyncClient() as client:
        # Quick connectivity check.
        try:
            r = await client.get(
                f'{AGENT_URL}/.well-known/agent-card.json',
                headers=A2A_HEADERS,
                timeout=5.0,
            )
            r.raise_for_status()
            print(f'Agent card found: {r.json().get("name", "?")}\n')
        except Exception as exc:  # noqa: BLE001
            print(f'\nERROR: Could not reach agent at {AGENT_URL}: {exc}')
            print('Make sure the agent is running: uv run python __main__.py')
            sys.exit(1)

        context_id, task_id = await test_approval_gate(client)
        await test_mid_task_steering(context_id, task_id, client)
        await test_streaming_and_confirm(client)

    print('\nAll 3 assertions passed.')


if __name__ == '__main__':
    asyncio.run(main())
