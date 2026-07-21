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

# ruff: noqa: S101, PLR2004  # pytest-idiomatic

"""Tests for bridge.config."""

import json

import pydantic
import pytest

from bridge import config


_REGISTRY = {
    'default': 'code',
    'agents': {
        'code': {
            'agent': 'agents/ix-ge',
            'display_name': 'Code Sandbox',
            'description': 'Runs code.',
            'tags': ['code'],
            'default_tools': [
                {'type': 'google_search'},
                {'type': 'mcp_server', 'name': 'g', 'url': 'https://x'},
            ],
        },
        'research': {
            'agent': 'antigravity-preview-05-2026',
            'display_name': 'Research',
            'description': 'Browses the web.',
            'default_environment': 'remote',
        },
    },
}


def test_load_from_inline_json() -> None:
    reg = config.AgentsRegistry.load(json.dumps(_REGISTRY))
    assert set(reg.agents) == {'code', 'research'}
    assert reg.default_agent.agent == 'agents/ix-ge'
    mcp = reg.agents['code'].default_tools[1]
    assert mcp.type == 'mcp_server'
    assert mcp.model_dump()['url'] == 'https://x'


def test_load_from_file(tmp_path) -> None:
    p = tmp_path / 'agents.json'
    p.write_text(json.dumps(_REGISTRY))
    reg = config.AgentsRegistry.load(str(p))
    assert reg.agents['research'].default_environment == 'remote'


def test_load_expands_substitutions() -> None:
    doc = dict(_REGISTRY)
    doc['agents'] = dict(doc['agents'])
    doc['agents']['code'] = dict(
        doc['agents']['code'],
        system_instruction='Query ${PROJECT_ID}.demo.q4_sales (cost $5).',
    )
    reg = config.AgentsRegistry.load(json.dumps(doc), {'PROJECT_ID': 'abhishekbhgwt-llm'})
    instruction = reg.agents['code'].system_instruction
    assert instruction is not None
    # Known placeholder expanded; an unrelated literal $ is left intact.
    assert 'abhishekbhgwt-llm.demo.q4_sales' in instruction
    assert 'cost $5' in instruction


def test_settings_registry_substitutes_project_id(tmp_path, monkeypatch) -> None:
    doc = dict(_REGISTRY)
    doc['agents'] = dict(doc['agents'])
    doc['agents']['code'] = dict(doc['agents']['code'], system_instruction='proj=${PROJECT_ID}')
    p = tmp_path / 'agents.json'
    p.write_text(json.dumps(doc))
    monkeypatch.setenv('PROJECT_ID', 'proj-x')
    monkeypatch.setenv('AGENTS_CONFIG', str(p))
    s = config.Settings()
    assert s.registry.agents['code'].system_instruction == 'proj=proj-x'


def test_unknown_default_rejected() -> None:
    bad = dict(_REGISTRY, default='nope')
    with pytest.raises(pydantic.ValidationError):
        config.AgentsRegistry.model_validate(bad)


def test_resolve_falls_back_to_default() -> None:
    reg = config.AgentsRegistry.model_validate(_REGISTRY)
    key, cfg = reg.resolve('missing')
    assert key == 'code'
    assert cfg.display_name == 'Code Sandbox'
    key, cfg = reg.resolve('research')
    assert key == 'research'


def test_settings_from_env(tmp_path, monkeypatch) -> None:
    p = tmp_path / 'agents.json'
    p.write_text(json.dumps(_REGISTRY))
    monkeypatch.setenv('PROJECT_ID', 'proj')
    monkeypatch.setenv('AGENTS_CONFIG', str(p))
    monkeypatch.setenv('IDLE_TTL_S', '120')
    s = config.Settings()
    assert s.project_id == 'proj'
    assert s.idle_ttl_s == 120
    assert s.registry.default == 'code'


def test_tool_type_aliased() -> None:
    assert config.Tool(type='mcp').type == 'mcp_server'


def test_control_plane_only_tool_rejected() -> None:
    with pytest.raises(pydantic.ValidationError, match='control-plane only'):
        config.Tool(type='filesystem')


def test_forward_user_auth_restricted_to_mcp() -> None:
    with pytest.raises(pydantic.ValidationError, match='forward_user_auth'):
        config.Tool(type='code_execution', forward_user_auth=True)
    t = config.Tool(type='mcp_server', forward_user_auth=True, url='https://x')
    assert t.forward_user_auth is True
