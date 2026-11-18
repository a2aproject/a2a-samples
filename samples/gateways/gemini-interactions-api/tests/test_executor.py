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

# ruff: noqa: S101, SLF001, S106  # pytest-idiomatic

"""Pure-logic unit tests for ``bridge.executor`` helpers.

Stateful turn behaviour (cancel, reattach, persist, owner-mismatch,
auth-required, env-id salvage) is covered in ``test_e2e.py`` against the real
TaskUpdater/EventQueue. This module keeps only the side-effect-free helpers:
``_session_key``, ``_vertex_overrides`` Struct conversion, ``_resolve_environment``
plus override gating, and the ``_open_stream`` tools / MCP-forward kwargs.
"""

from __future__ import annotations

import json
import logging

from typing import TYPE_CHECKING, Any
from unittest import mock

import pydantic
import pytest

from a2a import types as a2a_types
from bridge import auth, config, executor, sessions
from bridge import runtime as runtime_mod
from google.protobuf import json_format


if TYPE_CHECKING:
    from tests import conftest


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
                },
                {'type': 'mcp_server', 'name': 'open', 'url': 'https://o'},
                {'type': 'google_search'},
            ],
            'default_environment': 'remote',
        }
    },
}


@pytest.fixture
def agent_executor(
    monkeypatch: pytest.MonkeyPatch,
    fake_client: conftest.FakeInteractionsClient,
) -> executor.InteractionsAgentExecutor:
    monkeypatch.setattr(auth, 'adc_credentials', lambda: mock.Mock(valid=True, token='t'))
    settings = config.Settings(project_id='p', agents_config=json.dumps(_REGISTRY), _env_file=None)
    built = executor.InteractionsAgentExecutor(settings, runtime_mod.Runtime())
    built._client = fake_client  # type: ignore[assignment]
    return built


def _user(token_kind: str) -> auth.GoogleUser:
    return auth.GoogleUser(sub='s', email='u@e', token='user-tok', token_kind=token_kind)


async def _drain(events: Any) -> None:
    async for _ in events:
        pass


# --- _resolve_environment + override gating -----------------------------------


def test_env_override_rejected_when_bound(
    agent_executor: executor.InteractionsAgentExecutor,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = sessions.Session(env_id='env-cached')
    agent_config = agent_executor._registry.default_agent
    with caplog.at_level(logging.WARNING):
        env = agent_executor._resolve_environment(
            session=session,
            overrides={'environment': 'env-other'},
            agent_config=agent_config,
            session_key='k',
        )
    assert env == 'env-cached'
    assert 'rejected' in caplog.text


def test_env_override_honoured_when_unbound(
    agent_executor: executor.InteractionsAgentExecutor,
) -> None:
    agent_config = agent_executor._registry.default_agent
    session = sessions.Session()
    assert (
        agent_executor._resolve_environment(
            session=session,
            overrides={'environment': 'env-x'},
            agent_config=agent_config,
            session_key='k',
        )
        == 'env-x'
    )
    assert (
        agent_executor._resolve_environment(
            session=session,
            overrides={},
            agent_config=agent_config,
            session_key='k',
        )
        == 'remote'
    )


# --- _session_key -------------------------------------------------------------


def test_session_key_is_caller_scoped(
    agent_executor: executor.InteractionsAgentExecutor,
) -> None:
    """Regression: session keys must include caller identity in both scopes."""
    user = _user('access')
    # Context scope (default): identity + context_id + agent.
    assert agent_executor._session_key(user, 'ctx', 'code') == f'{user.identity}:ctx:code'
    assert agent_executor._session_key(None, 'ctx', 'code') == 'anon:ctx:code'
    # User scope: identity + agent (anonymous still falls through to context).
    agent_executor._settings = agent_executor._settings.model_copy(update={'env_scope': 'user'})
    assert agent_executor._session_key(user, 'ctx', 'code') == f'{user.identity}:code'
    assert agent_executor._session_key(None, 'ctx', 'code') == 'anon:ctx:code'


# --- _vertex_overrides Struct conversion --------------------------------------


def test_vertex_overrides_converts_proto_struct() -> None:
    """Regression: ``message.metadata`` is a protobuf Struct (a Mapping but no
    ``.get``); ``_vertex_overrides`` must convert it before reading."""
    msg = json_format.ParseDict(
        {
            'messageId': 'm',
            'role': 'ROLE_USER',
            'metadata': {'vertex': {'agent': 'code', 'tools': [{'type': 'x'}]}},
        },
        a2a_types.Message(),
    )
    ctx = mock.Mock(message=msg)
    out = executor._vertex_overrides(ctx)
    assert out['agent'] == 'code'
    assert out['tools'] == [{'type': 'x'}]


# --- _open_stream tools / MCP-forward kwargs ----------------------------------


@pytest.mark.asyncio
async def test_mcp_forward_only_with_access_token_and_flag(
    agent_executor: executor.InteractionsAgentExecutor,
    fake_client: conftest.FakeInteractionsClient,
) -> None:
    agent_config = agent_executor._registry.default_agent
    session = sessions.Session()

    def open_with(user: auth.GoogleUser | None) -> Any:
        return agent_executor._open_stream(
            agent_config=agent_config,
            overrides={},
            session=session,
            session_key='k',
            content_items=[],
            user=user,
            on_open=lambda r: None,
        )

    await _drain(open_with(_user('access')))
    by_name = {t.get('name'): t for t in fake_client.created[-1]['tools']}
    assert by_name['bq']['headers']['Authorization'] == 'Bearer user-tok'
    assert 'headers' not in by_name['open']
    assert all('forward_user_auth' not in t for t in fake_client.created[-1]['tools'])

    await _drain(open_with(_user('id')))
    assert all('headers' not in t for t in fake_client.created[-1]['tools'])

    await _drain(open_with(None))
    assert all('headers' not in t for t in fake_client.created[-1]['tools'])


@pytest.mark.asyncio
async def test_overrides_gated_by_setting(
    agent_executor: executor.InteractionsAgentExecutor,
    fake_client: conftest.FakeInteractionsClient,
) -> None:
    agent_config = agent_executor._registry.default_agent
    overrides = {
        'agent_ref': 'agents/evil',
        'tools': [{'type': 'code_execution'}],
        'agent_config': {'model': 'x'},
    }

    def open_with(allow: bool) -> Any:
        agent_executor._settings = agent_executor._settings.model_copy(
            update={'allow_request_overrides': allow}
        )
        return agent_executor._open_stream(
            agent_config=agent_config,
            overrides=overrides,
            session=sessions.Session(),
            session_key='k',
            content_items=[],
            user=None,
            on_open=lambda r: None,
        )

    # Default: agent_ref/tools/agent_config ignored.
    await _drain(open_with(False))
    call = fake_client.created[-1]
    assert call['agent'] == 'agents/a'
    assert call['agent_config'] is None
    assert all(t['type'] != 'code_execution' for t in call['tools'])

    # Enabled: applied, and override tools validated through config.Tool.
    await _drain(open_with(True))
    call = fake_client.created[-1]
    assert call['agent'] == 'agents/evil'
    assert call['agent_config'] == {'model': 'x'}
    assert any(t['type'] == 'code_execution' for t in call['tools'])

    # Enabled but invalid tool -> validation error, not silent injection.
    overrides['tools'] = [{'type': 'filesystem'}]
    with pytest.raises(pydantic.ValidationError):
        await _drain(open_with(True))
