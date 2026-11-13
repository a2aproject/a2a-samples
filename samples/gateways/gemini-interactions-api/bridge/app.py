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

"""Starlette application factory and path-based agent routing."""

from __future__ import annotations

import contextlib
import logging

from typing import TYPE_CHECKING

from a2a import types as a2a_types
from a2a.server import request_handlers
from a2a.server import routes as a2a_routes
from a2a.server import tasks as a2a_tasks
from a2a.server.routes import common as a2a_routes_common
from a2a.utils import constants as a2a_constants
from cli import card
from google.protobuf import json_format
from starlette import applications, middleware, routing
from starlette import exceptions as st_exceptions
from starlette import requests as st_requests
from starlette import responses as st_responses
from starlette import types as st_types
from starlette.middleware import authentication as auth_middleware
from starlette.middleware import base as middleware_base

from bridge import auth, config, executor
from bridge import runtime as runtime_mod


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from a2a.auth import user as a2a_user


logger = logging.getLogger(__name__)


def _is_public_path(path: str) -> bool:
    """Paths reachable without authentication (agent cards + health)."""
    return path.startswith('/healthz') or path.endswith(a2a_constants.AGENT_CARD_WELL_KNOWN_PATH)


def on_auth_error(_conn: st_requests.HTTPConnection, exc: Exception) -> st_responses.Response:
    """Returns a 401 JSON response for an authentication failure."""
    return st_responses.JSONResponse({'error': str(exc)}, status_code=401)


class _CallContextBuilder(a2a_routes_common.DefaultServerCallContextBuilder):
    """Passes ``GoogleUser`` to the executor unwrapped so it sees the bearer."""

    def build_user(self, request: st_requests.Request) -> a2a_user.User:
        user = request.scope.get('user')
        if isinstance(user, auth.GoogleUser):
            return user
        return super().build_user(request)


class AgentPathMiddleware(middleware_base.BaseHTTPMiddleware):
    """Enforces auth and injects ``x-bridge-agent`` from the path prefix."""

    def __init__(
        self,
        app: st_types.ASGIApp,
        agent_keys: frozenset[str],
        allow_anonymous: bool,
    ) -> None:
        """Wraps *app*; routes the first path segment if in *agent_keys*."""
        super().__init__(app)
        self._agent_keys = agent_keys
        self._allow_anonymous = allow_anonymous

    async def dispatch(
        self,
        request: st_requests.Request,
        call_next: middleware_base.RequestResponseEndpoint,
    ) -> st_responses.Response:
        """Enforces auth, then routes the first path segment to its agent."""
        path = request.url.path
        if (
            not request.user.is_authenticated
            and not self._allow_anonymous
            and not _is_public_path(path)
        ):
            return st_responses.JSONResponse({'error': 'missing user credentials'}, status_code=401)
        agent_segment = path.strip('/').split('/', 1)[0]
        if agent_segment in self._agent_keys:
            request.scope['headers'] = [
                *request.scope['headers'],
                (config.AGENT_HEADER.encode(), agent_segment.encode()),
            ]
        return await call_next(request)


def _request_base_url(request: st_requests.Request) -> str:
    """Returns the scheme+host base URL advertised to the caller.

    The host is read from the ``Host`` header and the scheme from
    ``X-Forwarded-Proto`` (falling back to the connection scheme for local
    dev). Cloud Run terminates TLS at its front end and forwards to the
    container over plain HTTP, so ``request.url.scheme`` is ``http``; the
    forwarded-proto header carries the real external ``https``. Trusting both
    is safe because Cloud Run overwrites them with the served values, so a
    caller cannot forge them; behind any other proxy the same guarantee must
    hold.

    Mirrors :meth:`bridge.auth._expected_audience`'s tolerant ``.get`` so a
    request without a ``Host`` header yields a controlled 400 rather than an
    uncaught ``KeyError`` (a 500) on this public, unauthenticated route.

    Raises:
      starlette.exceptions.HTTPException: 400 if the request has no ``Host``
        header.
    """
    host = request.headers.get('host')
    if not host:
        raise st_exceptions.HTTPException(status_code=400, detail='missing Host header')
    # X-Forwarded-Proto may be a comma-separated list across multiple proxies;
    # the originating scheme is the first entry.
    forwarded = (request.headers.get('x-forwarded-proto') or '').split(',')[0].strip()
    scheme = forwarded or request.url.scheme
    return f'{scheme}://{host}'


def build_app(settings: config.Settings) -> applications.Starlette:
    """Constructs the Starlette app for *settings*."""
    registry = settings.registry
    # The proto shape differs from the wire shape (e.g. wire ``security`` is the
    # proto's ``securityRequirements``), so ParseDict is lossy. The handler only
    # reads ``capabilities.*``, which is URL-independent; the card route builds
    # and serves the full dict per request from the request host.
    agent_card = json_format.ParseDict(
        card.build(registry, ''),
        a2a_types.AgentCard(),
        ignore_unknown_fields=True,
    )
    runtime = runtime_mod.Runtime()
    agent_executor = executor.InteractionsAgentExecutor(settings, runtime)

    handler = request_handlers.DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=a2a_tasks.InMemoryTaskStore(),
        agent_card=agent_card,
    )

    async def list_sessions(
        request: st_requests.Request,
    ) -> st_responses.Response:
        user = request.user
        if not isinstance(user, auth.GoogleUser):
            return st_responses.JSONResponse({'error': 'authentication required'}, status_code=401)
        sessions = await agent_executor.session_store.list_for(user.identity)
        return st_responses.JSONResponse({'sessions': [session.describe() for session in sessions]})

    def serve_card(prefix: str, key: str | None) -> routing.Route:
        def handle(request: st_requests.Request) -> st_responses.Response:
            return st_responses.JSONResponse(card.build(registry, _request_base_url(request), key))

        return routing.Route(
            prefix + a2a_constants.AGENT_CARD_WELL_KNOWN_PATH,
            handle,
            methods=['GET'],
        )

    context_builder = _CallContextBuilder()

    def agent_routes(prefix: str, key: str | None) -> list[routing.BaseRoute]:
        return [
            serve_card(prefix, key),
            *a2a_routes.create_jsonrpc_routes(
                handler,
                prefix or '/',
                context_builder=context_builder,
                enable_v0_3_compat=True,
            ),
        ]

    routes: list[routing.BaseRoute] = [
        routing.Route('/sessions', list_sessions, methods=['GET']),
        *agent_routes('', None),
    ]
    for key in registry.agents:
        routes.extend(agent_routes(f'/{key}', key))

    @contextlib.asynccontextmanager
    async def lifespan(_app: applications.Starlette) -> AsyncIterator[None]:
        sweeper = agent_executor.session_store.start_sweeper(settings.idle_ttl_s)
        try:
            yield
        finally:
            if sweeper is not None:
                sweeper.cancel()
            await agent_executor.aclose()
            await runtime.aclose()

    return applications.Starlette(
        routes=routes,
        lifespan=lifespan,
        middleware=[
            middleware.Middleware(
                auth_middleware.AuthenticationMiddleware,
                backend=auth.GoogleIdentityBackend(settings, runtime),
                on_error=on_auth_error,
            ),
            middleware.Middleware(
                AgentPathMiddleware,
                agent_keys=frozenset(registry.agents),
                allow_anonymous=settings.allow_anonymous,
            ),
        ],
    )
