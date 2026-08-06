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

# ruff: noqa: S101, SLF001  # pytest-idiomatic

"""Smoke tests for pure CLI helpers (no network, no Vertex calls)."""

from __future__ import annotations

import argparse
import base64
import io
import json
import zipfile

from typing import TYPE_CHECKING, Any
from unittest import mock

import pytest

from bridge import config
from cli import agents, authz, http, skills


if TYPE_CHECKING:
    import pathlib


def _agent_config(agent: str = 'agents/foo') -> config.AgentConfig:
    return config.AgentConfig(agent=agent, display_name='Foo', description='a foo agent')


# --- cli/agents.py ------------------------------------------------------------


def test_agent_id_strips_prefix() -> None:
    assert agents._agent_id(_agent_config('agents/my-agent')) == 'my-agent'


def test_agent_id_rejects_base_model() -> None:
    with pytest.raises(http.CliError, match='base model'):
        agents._agent_id(_agent_config('gemini-pro'))


def test_build_body_includes_defaults_and_extra_tools() -> None:
    args = argparse.Namespace(
        extra_tools=json.dumps([{'type': 'mcp_server', 'name': 'bq'}]),
        bucket='my-bucket',
        skill_registry_source='skills/123',
        service_account='sa@example.iam.gserviceaccount.com',
        base_model='antigravity',
    )
    body = agents._build_body(_agent_config(), args)
    assert body['base_agent'] == 'antigravity'
    assert body['description'] == 'a foo agent'
    tool_types = [t['type'] for t in body['tools']]
    assert 'code_execution' in tool_types
    assert 'mcp_server' in tool_types
    env = body['base_environment']
    assert env['service_account'] == 'sa@example.iam.gserviceaccount.com'
    targets = [source['target'] for source in env['sources']]
    assert './agent' in targets
    assert './skills' in targets


def test_load_body_file_substitutes_and_drops_id(
    tmp_path: pathlib.Path,
) -> None:
    body_file = tmp_path / 'body.json'
    body_file.write_text(
        json.dumps({'id': 'drop-me', 'bucket': 'gs://${BUCKET}', 'project': '${PROJECT_ID}'})
    )
    body = agents._load_body_file(body_file, project='proj-1', bucket='buck-1')
    assert 'id' not in body
    assert body['bucket'] == 'gs://buck-1'
    assert body['project'] == 'proj-1'


# --- cli/skills.py ------------------------------------------------------------


def test_srs_endpoint_default_and_override() -> None:
    assert (
        skills._srs_endpoint('us-central1', None) == 'https://us-central1-aiplatform.googleapis.com'
    )
    assert skills._srs_endpoint('us-central1', 'https://x') == 'https://x'


def test_description_uses_first_content_line(
    tmp_path: pathlib.Path,
) -> None:
    skill_dir = tmp_path / 'my-skill'
    skill_dir.mkdir()
    (skill_dir / 'SKILL.md').write_text('# Heading\n\n   \nThe real description.\nmore text\n')
    assert skills._description(skill_dir, 'fallback') == 'The real description.'


def test_description_falls_back_without_doc(tmp_path: pathlib.Path) -> None:
    skill_dir = tmp_path / 'empty-skill'
    skill_dir.mkdir()
    assert skills._description(skill_dir, 'fallback') == 'fallback'


def test_zip_b64_round_trips_files(tmp_path: pathlib.Path) -> None:
    skill_dir = tmp_path / 'skill'
    (skill_dir / 'nested').mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('doc')
    (skill_dir / 'nested' / 'tool.py').write_text('print(1)')

    encoded = skills._zip_b64(skill_dir)
    archive = zipfile.ZipFile(io.BytesIO(base64.b64decode(encoded)))
    names = set(archive.namelist())
    assert names == {'SKILL.md', 'nested/tool.py'}
    assert archive.read('SKILL.md') == b'doc'


# --- cli/authz.py -------------------------------------------------------------


def test_authz_encodes_scopes_with_percent20_and_redacts_secret(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Regression: scopes in authorizationUri must be ``%20``-joined (a ``+``
    would be re-encoded by GE into ``%2B`` and corrupt the scope list); the
    printed result must not leak the client secret."""
    sent: dict[str, Any] = {}

    class _Session:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def upsert(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
            sent['body'] = _args[2]
            return {
                'name': 'authz-1',
                'serverSideOauth2': {'clientSecret': 'leaked'},
            }

    monkeypatch.setattr(authz.sys, 'stdin', io.StringIO('super-secret\n'))
    monkeypatch.setattr(authz.http, 'AuthedSession', _Session)
    args = argparse.Namespace(
        client_secret_stdin=True,
        secret_from_secret_manager=None,
        oauth_client_id='client-123',
        name='authz-1',
        project='proj',
        scope=None,
    )

    authz.run(args, mock.Mock())

    oauth = sent['body']['serverSideOauth2']
    assert oauth['clientSecret'] == 'super-secret'
    assert '%20' in oauth['authorizationUri']
    assert 'scope=openid+email' not in oauth['authorizationUri']
    printed = capsys.readouterr().out
    assert 'leaked' not in printed
