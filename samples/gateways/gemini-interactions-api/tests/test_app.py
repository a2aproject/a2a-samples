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

"""Tests for bridge.app routing."""

from __future__ import annotations

import json

import pytest

from bridge import app, auth, config
from cli import card
from starlette import testclient


_AGENTS = json.dumps(
    {
        'default': 'a',
        'agents': {
            'a': {'agent': 'agents/x', 'display_name': 'A', 'description': 'd'},
        },
    }
)


# TestClient sends Host: testserver over http, so the served card advertises
# the request-derived base URL ``http://testserver``.
_BASE_URL = 'http://testserver'


@pytest.fixture
def served_app(monkeypatch: pytest.MonkeyPatch) -> testclient.TestClient:
    monkeypatch.setattr(auth, 'adc_credentials', lambda: None)
    settings = config.Settings(
        project_id='p',
        agents_config=_AGENTS,
        allow_anonymous=True,
    )
    with testclient.TestClient(app.build_app(settings)) as client:
        yield client


def test_served_card_matches_cli(served_app: testclient.TestClient) -> None:
    """Regression: ParseDict drops securitySchemes; route serves the dict."""
    body = served_app.get('/.well-known/agent-card.json').json()
    assert body['securitySchemes']['google_oidc']['type'] == 'openIdConnect'
    assert body['securitySchemes']['google_oauth2']['type'] == 'oauth2'
    assert body['security']
    registry = config.AgentsRegistry.load(_AGENTS)
    assert body == card.build(registry, _BASE_URL)


def test_served_card_per_agent(served_app: testclient.TestClient) -> None:
    body = served_app.get('/a/.well-known/agent-card.json').json()
    assert body['url'] == f'{_BASE_URL}/a'
    assert [s['id'] for s in body['skills']] == ['a']
    assert body['securitySchemes']['google_oidc']


def test_served_card_honors_forwarded_proto(
    served_app: testclient.TestClient,
) -> None:
    """Behind Cloud Run the container hop is HTTP; X-Forwarded-Proto carries
    the real external scheme, so the advertised URL must be https."""
    body = served_app.get(
        '/a/.well-known/agent-card.json',
        headers={'x-forwarded-proto': 'https'},
    ).json()
    assert body['url'] == 'https://testserver/a'


def test_card_paths_public_without_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: per-agent ``/{key}/.well-known/agent-card.json`` must be
    reachable without credentials, just like the root well-known path."""
    monkeypatch.setattr(auth, 'adc_credentials', lambda: None)
    settings = config.Settings(
        project_id='p',
        agents_config=_AGENTS,
        allow_anonymous=False,
    )
    with testclient.TestClient(app.build_app(settings)) as client:
        assert client.get('/.well-known/agent-card.json').status_code == 200
        assert client.get('/a/.well-known/agent-card.json').status_code == 200
        assert client.post('/').status_code == 401
