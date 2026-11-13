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

# ruff: noqa: S101, SLF001, S105, S106, SIM117, PLR0913, PLC0415  # pytest-idiomatic

"""Tests for bridge.auth and the auth middleware stack."""

from __future__ import annotations

import types

from unittest import mock

import httpx
import pytest

from bridge import app, auth
from bridge import runtime as runtime_mod
from starlette import applications, authentication, middleware, responses, routing, testclient
from starlette.middleware import authentication as auth_middleware


def _conn(header: str | None) -> types.SimpleNamespace:
    headers = {'authorization': header} if header else {}
    return types.SimpleNamespace(headers=headers)


def _backend(
    runtime: runtime_mod.Runtime,
    aud: str | None = 'http://t',
    *,
    allow_no_aud: bool = False,
) -> auth.GoogleIdentityBackend:
    settings = types.SimpleNamespace(
        id_token_audience=aud,
        allow_unverified_id_token_audience=allow_no_aud,
    )
    return auth.GoogleIdentityBackend(settings, runtime)


@pytest.mark.asyncio
async def test_backend_absent_header_returns_none(
    runtime: runtime_mod.Runtime,
) -> None:
    assert await _backend(runtime).authenticate(_conn(None)) is None


@pytest.mark.asyncio
async def test_backend_id_token_ok(runtime: runtime_mod.Runtime) -> None:
    with mock.patch.object(
        auth.google_id_token,
        'verify_oauth2_token',
        return_value={'sub': '123', 'email': 'u@e'},
    ) as verify:
        creds, user = await _backend(runtime).authenticate(_conn('Bearer a.b.c'))
    verify.assert_called_once()
    assert verify.call_args.args[0] == 'a.b.c'
    assert verify.call_args.args[2] == 'http://t'
    assert isinstance(user, auth.GoogleUser)
    assert user.token_kind == 'id'
    assert user.email == 'u@e'
    assert 'authenticated' in creds.scopes


@pytest.mark.asyncio
async def test_backend_id_token_bad_aud_raises(
    runtime: runtime_mod.Runtime,
) -> None:
    with (
        mock.patch.object(
            auth.google_id_token,
            'verify_oauth2_token',
            side_effect=ValueError('Wrong audience'),
        ),
        pytest.raises(authentication.AuthenticationError),
    ):
        await _backend(runtime).authenticate(_conn('Bearer a.b.c'))


@pytest.mark.asyncio
async def test_backend_id_token_rejected_without_audience(
    runtime: runtime_mod.Runtime,
) -> None:
    """Regression: with no aud configured, ID tokens must be rejected rather
    than verified with audience=None (which would skip the aud check)."""
    with mock.patch.object(auth.google_id_token, 'verify_oauth2_token') as verify:
        with pytest.raises(authentication.AuthenticationError):
            await _backend(runtime, aud=None).authenticate(_conn('Bearer a.b.c'))
    verify.assert_not_called()


@pytest.mark.asyncio
async def test_backend_id_token_no_audience_opt_out(
    runtime: runtime_mod.Runtime,
) -> None:
    with mock.patch.object(
        auth.google_id_token,
        'verify_oauth2_token',
        return_value={'sub': 's'},
    ) as verify:
        _, user = await _backend(runtime, aud=None, allow_no_aud=True).authenticate(
            _conn('Bearer a.b.c')
        )
    assert verify.call_args.args[2] is None
    assert user.token_kind == 'id'


class _FakeResp:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload

    def raise_for_status(self) -> None:
        return None


@pytest.mark.asyncio
async def test_backend_access_token_ok(
    runtime: runtime_mod.Runtime,
) -> None:
    async def fake_get(_url: str, params: dict[str, str]) -> _FakeResp:
        assert params['access_token'] == 'opaque-tok'
        return _FakeResp({'sub': 's', 'email': 'u@e'})

    with mock.patch.object(runtime.http, 'get', side_effect=fake_get):
        _, user = await _backend(runtime).authenticate(_conn('Bearer opaque-tok'))
    assert user.token_kind == 'access'
    assert user.email == 'u@e'
    assert user.identity


@pytest.mark.asyncio
async def test_backend_access_token_cached(
    runtime: runtime_mod.Runtime,
) -> None:
    get = mock.AsyncMock(return_value=_FakeResp({'sub': 's'}))
    backend = _backend(runtime)
    with mock.patch.object(runtime.http, 'get', get):
        await backend.authenticate(_conn('Bearer opaque-tok'))
        await backend.authenticate(_conn('Bearer opaque-tok'))
    assert get.call_count == 1


@pytest.mark.asyncio
async def test_backend_rejects_non_bearer_scheme(
    runtime: runtime_mod.Runtime,
) -> None:
    with pytest.raises(authentication.AuthenticationError, match='Bearer'):
        await _backend(runtime).authenticate(_conn('Basic Zm9v'))


@pytest.mark.asyncio
async def test_backend_no_subject_raises(
    runtime: runtime_mod.Runtime,
) -> None:

    async def fake_get(_url: str, params: dict[str, str]) -> _FakeResp:
        del params
        return _FakeResp({'aud': 'x'})

    with mock.patch.object(runtime.http, 'get', side_effect=fake_get):
        with pytest.raises(authentication.AuthenticationError, match='no sub/email'):
            await _backend(runtime).authenticate(_conn('Bearer no-subject'))


def _mini_app(runtime: runtime_mod.Runtime, allow_anonymous: bool) -> applications.Starlette:
    async def ok(_req: object) -> responses.Response:
        return responses.PlainTextResponse('ok')

    return applications.Starlette(
        routes=[
            routing.Route('/', ok, methods=['POST']),
            routing.Route('/.well-known/agent-card.json', ok),
        ],
        middleware=[
            middleware.Middleware(
                auth_middleware.AuthenticationMiddleware,
                backend=_backend(runtime),
                on_error=app.on_auth_error,
            ),
            middleware.Middleware(
                app.AgentPathMiddleware,
                agent_keys=frozenset(),
                allow_anonymous=allow_anonymous,
            ),
        ],
    )


@pytest.mark.parametrize(
    ('allow_anonymous', 'method', 'path', 'auth_header', 'expected'),
    [
        (False, 'POST', '/', None, 401),
        (False, 'GET', '/.well-known/agent-card.json', None, 200),
        (False, 'POST', '/', 'Bearer not-a-jwt', 401),
        (False, 'POST', '/', 'Basic Zm9v', 401),
        (False, 'POST', '/', 'Bearer a.b.c', 200),
        (True, 'POST', '/', None, 200),
    ],
)
def test_middleware_paths(
    runtime: runtime_mod.Runtime,
    monkeypatch: pytest.MonkeyPatch,
    allow_anonymous: bool,
    method: str,
    path: str,
    auth_header: str | None,
    expected: int,
) -> None:
    monkeypatch.setattr(
        auth.google_id_token,
        'verify_oauth2_token',
        lambda *_a, **_k: {'sub': 's'},
    )
    monkeypatch.setattr(
        runtime.http,
        'get',
        mock.AsyncMock(side_effect=httpx.HTTPError('blocked')),
    )
    headers = {'Authorization': auth_header} if auth_header else {}
    with testclient.TestClient(_mini_app(runtime, allow_anonymous=allow_anonymous)) as client:
        resp = client.request(method, path, headers=headers)
    assert resp.status_code == expected


def test_call_context_builder_passes_google_user_unwrapped() -> None:
    """Regression: GoogleUser must reach the executor unwrapped.

    The SDK's default builder wraps ``request.user`` in ``StarletteUser``,
    which hides ``GoogleUser.token`` from ``executor._user()`` and breaks MCP
    token forwarding.
    """
    from starlette import requests as st_requests

    user = auth.GoogleUser(sub='s', email='e@x', token='tok', token_kind='access')
    request = st_requests.Request(
        {
            'type': 'http',
            'headers': [],
            'user': user,
            'auth': authentication.AuthCredentials(['authenticated']),
        }
    )
    ctx = app._CallContextBuilder().build(request)
    assert ctx.user is user
    assert isinstance(ctx.user, auth.GoogleUser)
    assert ctx.user.token == 'tok'
