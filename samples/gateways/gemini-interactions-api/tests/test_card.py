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

"""Tests for cli.card."""

import json

from bridge import config
from cli import card


_REGISTRY = config.AgentsRegistry.model_validate(
    {
        'default': 'a',
        'agents': {
            'a': {
                'agent': 'agents/x',
                'display_name': 'A',
                'description': 'first',
                'tags': ['t'],
            },
            'b': {
                'agent': 'agents/y',
                'display_name': 'B',
                'description': 'second',
            },
        },
    }
)


def test_card_advertises_adk_extension() -> None:
    out = card.build(_REGISTRY, 'https://h')
    exts = out['capabilities']['extensions']
    assert any(e['uri'] == card._ADK_A2A_EXTENSION for e in exts)
    assert out['capabilities']['streaming'] is True


def test_card_security_schemes_present() -> None:
    out = card.build(_REGISTRY, 'https://h')
    schemes = out['securitySchemes']
    assert schemes['google_oidc']['type'] == 'openIdConnect'
    assert schemes['google_oauth2']['type'] == 'oauth2'
    assert {'google_oidc': []} in out['security']
    assert json.dumps(out)


def test_card_multi_agent_description_folds_skills() -> None:
    out = card.build(_REGISTRY, 'https://h')
    assert 'A' in out['description'] and 'B' in out['description']
    assert {s['id'] for s in out['skills']} == {'a', 'b'}


def test_card_single_agent_scoped_url() -> None:
    out = card.build(_REGISTRY, 'https://h', key='b')
    assert out['url'] == 'https://h/b'
    assert len(out['skills']) == 1
    assert out['description'] == 'second'
