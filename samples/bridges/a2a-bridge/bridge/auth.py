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

"""Caller identity verification and ADC helpers.

Incoming ``Authorization: Bearer <token>`` headers are verified by
:class:`GoogleIdentityBackend`, which accepts both Google-signed ID tokens
(local signature + audience check) and opaque OAuth2 access tokens
(validated via the tokeninfo endpoint). The resulting :class:`GoogleUser`
is exposed on ``request.user`` and copied onto the a2a-sdk
``ServerCallContext`` for the executor to consume.
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import logging
import time

from typing import TYPE_CHECKING, Any, Literal

import httpx

from a2a.auth import user as a2a_user
from google import auth as google_auth
from google.auth import credentials as auth_credentials
from google.auth import exceptions as auth_exceptions
from google.auth.transport import requests as auth_requests
from google.oauth2 import id_token as google_id_token
from starlette import authentication


if TYPE_CHECKING:
    from bridge import config
    from bridge import runtime as runtime_mod


logger = logging.getLogger(__name__)

_TOKENINFO_URL = 'https://oauth2.googleapis.com/tokeninfo'


def _digest(value: str) -> str:
    """Returns a 32-hex-char (128-bit) SHA-256 digest for pseudonymous keys.

    128 bits keeps accidental collisions negligible even at large user counts,
    so two callers never share a session-owner key.
    """
    return hashlib.sha256(value.encode()).hexdigest()[:32]


class GoogleUser(authentication.SimpleUser, a2a_user.User):
    """A Google-authenticated caller, exposed on ``request.user``.

    Constructed by :class:`GoogleIdentityBackend` after either an ID token
    signature check or a successful tokeninfo lookup. Carries the original
    bearer token so it can be forwarded to opt-in MCP tools via
    ``forward_user_auth``; see :mod:`bridge.executor`.
    """

    def __init__(
        self,
        *,
        sub: str | None,
        email: str | None,
        token: str,
        token_kind: Literal['id', 'access'],
    ) -> None:
        """Constructs a verified caller principal.

        Args:
          sub: The token's ``sub`` claim, if present.
          email: The token's ``email`` claim, if present.
          token: The raw bearer token, retained for downstream MCP forwarding.
          token_kind: ``"id"`` for Google ID tokens; ``"access"`` for OAuth2
            access tokens. Only access tokens are forwarded to MCP tools.

        Raises:
          ValueError: If both *sub* and *email* are None.
        """
        if not (sub or email):
            raise ValueError('GoogleUser requires sub or email')
        super().__init__(email or sub or 'google-user')
        self.sub = sub
        self.email = email
        self.token = token
        self.token_kind = token_kind

    @property
    def user_name(self) -> str:
        """Satisfies ``a2a.auth.user.User``."""
        return self.display_name

    @property
    def identity(self) -> str:
        """Stable pseudonymous key for session scoping."""
        subject = self.sub or self.email or ''
        return _digest(subject)


class GoogleIdentityBackend(authentication.AuthenticationBackend):
    """Verifies Google ID tokens and OAuth2 access tokens."""

    def __init__(self, settings: config.Settings, runtime: runtime_mod.Runtime) -> None:
        """Caches the audience override and the unverified-audience escape."""
        self._aud_override = settings.id_token_audience
        self._allow_no_aud = settings.allow_unverified_id_token_audience
        self._runtime = runtime

    async def authenticate(
        self, conn: authentication.HTTPConnection
    ) -> tuple[authentication.AuthCredentials, GoogleUser] | None:
        """Verifies the ``Authorization`` header, if present.

        Three-segment tokens are verified as Google ID tokens (signature +
        audience check). Other tokens are validated against the tokeninfo
        endpoint and cached until each token expires (or a configured
        default if no expiry is reported).

        Returns:
          ``None`` if no ``Authorization`` header was sent. Otherwise the
          authenticated credentials and user.

        Raises:
          starlette.authentication.AuthenticationError: If a token is
            present but invalid (bad signature, wrong audience, expired,
            missing sub/email, network error to tokeninfo).
        """
        header_value = conn.headers.get('authorization')
        if not header_value:
            return None
        scheme, _, token = header_value.partition(' ')
        if scheme.lower() != 'bearer' or not token:
            raise authentication.AuthenticationError(
                "Authorization header must be 'Bearer <token>'"
            )
        try:
            if token.count('.') == 2:  # noqa: PLR2004
                aud = self._expected_audience(conn)
                if aud is None and not self._allow_no_aud:
                    raise authentication.AuthenticationError(
                        'ID-token authentication requires ID_TOKEN_AUDIENCE or a '
                        'resolvable request host'
                    )
                claims = await asyncio.to_thread(
                    google_id_token.verify_oauth2_token,
                    token,
                    auth_requests.Request(),
                    aud,
                )
                token_kind: Literal['id', 'access'] = 'id'  # noqa: S105
            else:
                claims = await self._tokeninfo(token)
                token_kind = 'access'  # noqa: S105
        except (
            auth_exceptions.GoogleAuthError,
            ValueError,
            httpx.HTTPError,
        ) as err:
            raise authentication.AuthenticationError(str(err)) from None
        if not (claims.get('sub') or claims.get('email')):
            raise authentication.AuthenticationError('token has no sub/email claim')
        user = GoogleUser(
            sub=claims.get('sub'),
            email=claims.get('email'),
            token=token,
            token_kind=token_kind,
        )
        logger.debug('auth user=%s kind=%s', user.display_name, token_kind)
        return authentication.AuthCredentials(['authenticated']), user

    def _expected_audience(self, conn: authentication.HTTPConnection) -> str | None:
        """Returns the audience an ID token must match, or None if unknown.

        The configured ``id_token_audience`` wins; otherwise the audience is
        derived from the request's ``Host`` header and ``X-Forwarded-Proto``
        scheme (Cloud Run forwards to the container over HTTP, so the scheme
        must come from the forwarded-proto header, not the connection). Trusting
        both is safe because Cloud Run overwrites them with the served values,
        so a caller cannot forge them; the card route advertises the same URL.
        """
        if self._aud_override:
            return self._aud_override
        host = conn.headers.get('host')
        if not host:
            return None
        # X-Forwarded-Proto may be a comma-separated list across multiple
        # proxies; the originating scheme is the first entry.
        forwarded = (conn.headers.get('x-forwarded-proto') or '').split(',')[0].strip()
        scheme = forwarded or conn.url.scheme
        return f'{scheme}://{host}'

    async def _tokeninfo(self, token: str) -> dict[str, Any]:
        """Validates an opaque OAuth2 access token via the tokeninfo endpoint.

        Results are cached under a digest of the token until the token's own
        ``expires_in`` elapses, falling back to the cache default TTL when
        ``expires_in`` is missing or unparsable.

        Args:
          token: The opaque OAuth2 access token to validate.

        Returns:
          The tokeninfo claims mapping.
        """
        cache = self._runtime.tokeninfo_cache
        key = _digest(token)
        if (cached := cache.get(key)) is not None:
            deadline, claims = cached
            if time.monotonic() < deadline:
                return claims
        resp = await self._runtime.http.get(_TOKENINFO_URL, params={'access_token': token})
        resp.raise_for_status()
        claims = resp.json()
        try:
            expires_in = max(0, int(claims.get('expires_in', cache.ttl)))
        except (TypeError, ValueError):
            expires_in = int(cache.ttl)
        cache[key] = (time.monotonic() + expires_in, claims)
        return claims


@functools.cache
def adc_credentials() -> auth_credentials.Credentials:
    """Process-wide Application Default Credentials with cloud-platform scope."""
    creds, _ = google_auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    return creds
