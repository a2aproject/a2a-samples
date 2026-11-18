# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ruff: noqa: S101, SLF001, S106, PLR2004, PERF203  # pytest-idiomatic

"""End-to-end tests: ``execute`` -> real TaskUpdater + EventQueue.

These drive the executor through the *real* ``a2a.server.tasks.TaskUpdater``
and ``a2a.server.events.EventQueue`` against a fake Vertex backend, then drain
the queue and assert on the resulting ``Task`` / ``TaskStatusUpdateEvent``
protos. They cover the stateful executor paths (stream+complete, cancel
mid-stream, reattach after a dropped stream, tool auth-required) that the unit
fakes cannot exercise faithfully.

A single Starlette ``message/send`` flow drives the same path through
``build_app`` to confirm the JSON-RPC wiring and the unwrapped ``GoogleUser``.
"""

from __future__ import annotations

import asyncio
import json

from typing import TYPE_CHECKING, Any
from unittest import mock

import httpx
import pytest

from a2a import types as a2a_types
from a2a.server.events import EventQueue
from bridge import app, auth, config, executor, interactions
from bridge import runtime as runtime_mod
from starlette import testclient

from tests import conftest


if TYPE_CHECKING:
    from collections.abc import AsyncIterator


_REGISTRY = {
    'default': 'code',
    'agents': {
        'code': {
            'agent': 'agents/a',
            'display_name': 'Code',
            'description': 'd',
            'default_tools': [
                {
                    'type': 'mcp_server',
                    'name': 'bq',
                    'url': 'https://bq',
                    'forward_user_auth': True,
                }
            ],
            'default_environment': 'remote',
        }
    },
}

_COMPLETED = a2a_types.TaskState.TASK_STATE_COMPLETED
_FAILED = a2a_types.TaskState.TASK_STATE_FAILED
_CANCELED = a2a_types.TaskState.TASK_STATE_CANCELED
_AUTH_REQUIRED = a2a_types.TaskState.TASK_STATE_AUTH_REQUIRED


def _settings(**overrides: Any) -> config.Settings:
    return config.Settings(
        project_id='p',
        agents_config=json.dumps(_REGISTRY),
        _env_file=None,
        **overrides,
    )


@pytest.fixture
def agent_executor(
    monkeypatch: pytest.MonkeyPatch,
    fake_client: conftest.FakeInteractionsClient,
) -> executor.InteractionsAgentExecutor:
    monkeypatch.setattr(auth, 'adc_credentials', lambda: mock.Mock(valid=True, token='t'))
    built = executor.InteractionsAgentExecutor(_settings(), runtime_mod.Runtime())
    built._client = fake_client  # type: ignore[assignment]
    return built


def _ctx(**overrides: Any) -> mock.Mock:
    ctx = mock.Mock(
        task_id='t',
        context_id='c',
        current_task=None,
        message=None,
        call_context=None,
    )
    for key, value in overrides.items():
        setattr(ctx, key, value)
    return ctx


async def _drain(queue: EventQueue) -> conftest.DrainedQueue:
    """Lets the dispatcher settle, then drains all enqueued protos."""
    await asyncio.sleep(0)
    events: list[Any] = []
    while True:
        try:
            events.append(queue.queue.get_nowait())
        except asyncio.QueueEmpty:
            break
    return conftest.DrainedQueue(events)


@pytest.mark.asyncio
async def test_stream_to_completion(
    agent_executor: executor.InteractionsAgentExecutor,
    fake_client: conftest.FakeInteractionsClient,
) -> None:
    fake_client.events = [
        conftest.interaction_created('ix-1', environment_id='env-1'),
        conftest.step_delta('text', event_id='e1', text='hello '),
        conftest.step_delta('text', event_id='e2', text='world'),
        conftest.step_stop(),
        conftest.interaction_completed(
            {'id': 'ix-1', 'output': [{'content': [{'type': 'text', 'text': 'all done'}]}]}
        ),
    ]
    queue = EventQueue()

    await agent_executor.execute(_ctx(), queue)
    drained = await _drain(queue)

    assert drained.task is not None
    assert drained.task.status.state == a2a_types.TaskState.TASK_STATE_SUBMITTED
    assert drained.terminal_state == _COMPLETED
    final = drained.status_events[-1].status.message
    assert final.parts[0].text == 'all done'
    # State persisted from the completed interaction.
    session = await agent_executor.session_store.get_or_create('anon:c:code')
    assert session.interaction_id == 'ix-1'
    assert session.env_id == 'env-1'


@pytest.mark.asyncio
async def test_cancel_mid_stream(
    agent_executor: executor.InteractionsAgentExecutor,
) -> None:
    """A cancel landing mid-stream cancels the active response, emits CANCELED,
    and suppresses both the terminal completion and any reattach."""
    release = asyncio.Event()
    cancel_seen = asyncio.Event()

    class _BlockingClient(conftest.FakeInteractionsClient):
        async def create(self, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
            self.created.append(kwargs)
            on_open = kwargs.get('on_open')
            if on_open is not None:
                on_open(self._response)
            yield conftest.interaction_created('ix', environment_id='env')
            cancel_seen.set()
            await release.wait()
            # The cancel closed the response; surface that as a dropped stream.
            raise httpx.RemoteProtocolError('peer closed connection')

    client = _BlockingClient()
    client._response = mock.AsyncMock()  # type: ignore[attr-defined]
    agent_executor._client = client  # type: ignore[assignment]

    execute_queue = EventQueue()
    cancel_queue = EventQueue()
    task = asyncio.ensure_future(agent_executor.execute(_ctx(), execute_queue))
    await cancel_seen.wait()
    await agent_executor.cancel(_ctx(), cancel_queue)
    release.set()
    await task

    client._response.aclose.assert_awaited_once()
    assert client.reattached == []
    execute_drained = await _drain(execute_queue)
    # No terminal completion/failure was emitted on the execute queue.
    assert _COMPLETED not in execute_drained.states
    assert _FAILED not in execute_drained.states
    cancel_drained = await _drain(cancel_queue)
    assert cancel_drained.terminal_state == _CANCELED


@pytest.mark.asyncio
async def test_reattach_after_remote_protocol_error(
    agent_executor: executor.InteractionsAgentExecutor,
    fake_client: conftest.FakeInteractionsClient,
) -> None:
    """A dropped stream reattaches with the last seen event id and completes."""
    fake_client.events = [
        conftest.interaction_created('ix-9', environment_id='env-9'),
        conftest.step_delta('text', event_id='e1', text='partial'),
    ]
    fake_client.create_error = httpx.RemoteProtocolError('dropped')
    fake_client.reattach_events = [
        conftest.step_delta('text', event_id='e2', text=' rest'),
        conftest.step_stop(),
        conftest.interaction_completed({'id': 'ix-9'}),
    ]
    queue = EventQueue()

    await agent_executor.execute(_ctx(), queue)
    drained = await _drain(queue)

    assert fake_client.reattached == [{'interaction_id': 'ix-9', 'last_event_id': 'e1'}]
    assert drained.terminal_state == _COMPLETED
    assert _FAILED not in drained.states


@pytest.mark.asyncio
async def test_tool_error_emits_auth_required(
    agent_executor: executor.InteractionsAgentExecutor,
    fake_client: conftest.FakeInteractionsClient,
) -> None:
    fake_client.events = [
        conftest.interaction_created('ix-2'),
        conftest.error_event({'code': 'unauthenticated', 'tool': 'bigquery'}),
    ]
    queue = EventQueue()

    await agent_executor.execute(_ctx(), queue)
    drained = await _drain(queue)

    assert drained.terminal_state == _AUTH_REQUIRED
    auth_message = drained.status_events[-1].status.message
    assert 'bigquery' in auth_message.parts[0].text
    assert _FAILED not in drained.states


@pytest.mark.asyncio
async def test_fail_salvages_env_id_from_get(
    agent_executor: executor.InteractionsAgentExecutor,
    fake_client: conftest.FakeInteractionsClient,
) -> None:
    """On failure with a known interaction, ``_fail`` salvages the env id via
    the configurable ``get`` result so the next turn can reattach."""
    fake_client.events = [
        conftest.interaction_created('ix-3'),
        conftest.status_update('failed'),
    ]
    fake_client.get_result = {'environment_id': 'salvaged-env'}
    queue = EventQueue()

    await agent_executor.execute(_ctx(context_id='ctx-salvage'), queue)
    drained = await _drain(queue)

    assert drained.terminal_state == _FAILED
    session = await agent_executor.session_store.get_or_create('anon:ctx-salvage:code')
    assert session.env_id == 'salvaged-env'


@pytest.mark.asyncio
async def test_owner_mismatch_starts_fresh_chain(
    agent_executor: executor.InteractionsAgentExecutor,
    fake_client: conftest.FakeInteractionsClient,
) -> None:
    """A session persisted under another caller must not be reattached: the
    executor drops the stolen env/interaction and starts a fresh chain."""
    fake_client.events = [conftest.interaction_completed({'id': 'ix'})]
    user = _user_access()
    key = agent_executor._session_key(user, 'c', 'code')
    pre = await agent_executor.session_store.get_or_create(key)
    pre.owner = 'someone-else'
    pre.env_id = 'stolen-env'
    pre.interaction_id = 'stolen-ix'

    queue = EventQueue()
    await agent_executor.execute(
        _ctx(call_context=mock.Mock(user=user, state={'headers': {}})),
        queue,
    )

    call = fake_client.created[-1]
    assert call['previous_interaction_id'] is None
    assert call['environment'] == 'remote'


def _user_access() -> auth.GoogleUser:
    return auth.GoogleUser(sub='s', email='u@e', token='user-tok', token_kind='access')


# --- Starlette JSON-RPC message/send flow -------------------------------------


def test_message_send_completes_with_unwrapped_user(
    monkeypatch: pytest.MonkeyPatch,
    fake_client: conftest.FakeInteractionsClient,
) -> None:
    """A real ``message/send`` request reaches COMPLETED, and the unwrapped
    ``GoogleUser`` access token is forwarded to the MCP tool (proving the
    executor saw the user, not the SDK's wrapped principal)."""
    fake_client.events = [
        conftest.interaction_created('ix', environment_id='env'),
        conftest.interaction_completed(
            {'id': 'ix', 'output': [{'content': [{'type': 'text', 'text': 'done!'}]}]}
        ),
    ]

    class _FakeTokenInfo:
        def json(self) -> dict[str, Any]:
            return {'sub': 's', 'email': 'u@e', 'expires_in': '3600'}

        def raise_for_status(self) -> None:
            return None

    async def fake_tokeninfo(*_args: Any, **_kwargs: Any) -> _FakeTokenInfo:
        return _FakeTokenInfo()

    monkeypatch.setattr(auth, 'adc_credentials', lambda: None)
    monkeypatch.setattr(interactions, 'InteractionsClient', lambda settings: fake_client)
    monkeypatch.setattr(runtime_mod.httpx.AsyncClient, 'get', fake_tokeninfo)

    with testclient.TestClient(app.build_app(_settings())) as client:
        resp = client.post(
            '/',
            headers={'Authorization': 'Bearer opaque-access-token'},
            json={
                'jsonrpc': '2.0',
                'id': '1',
                'method': 'message/send',
                'params': {
                    'message': {
                        'role': 'user',
                        'parts': [{'text': 'hi'}],
                        'message_id': 'm1',
                    }
                },
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body['result']['status']['state'] == 'completed'
    forwarded = fake_client.created[-1]['tools']
    assert forwarded[0]['headers']['Authorization'] == 'Bearer opaque-access-token'
