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

"""Async client for the Vertex Agents Interactions API (SSE streaming)."""

from __future__ import annotations

import asyncio
import json
import logging

from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from typing import Any

import httpx

from google.auth.transport import requests as auth_requests

from bridge import auth, config


logger = logging.getLogger(__name__)

OnOpen = Callable[[httpx.Response], None]

_CONNECT_TIMEOUT_S = 30.0

_SSE_DATA_PREFIX = 'data: '


class InteractionsClient:
    """Async client for Vertex ``v1beta1/interactions`` with SSE parsing.

    Authenticates as the bridge service account via ADC. Construct once
    per process; ``aclose()`` at shutdown.
    """

    def __init__(self, settings: config.Settings) -> None:
        """Opens an httpx client; ADC credentials are lazily refreshed."""
        self._settings = settings
        self._creds = auth.adc_credentials()
        self._refresh_lock = asyncio.Lock()
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(
                None,
                connect=_CONNECT_TIMEOUT_S,
                read=settings.stream_read_timeout_s,
            )
        )

    async def aclose(self) -> None:
        """Closes the underlying httpx client; call once at process shutdown."""
        await self._http.aclose()

    @property
    def _base_url(self) -> str:
        settings = self._settings
        return (
            f'{settings.vertex_endpoint}/v1beta1'
            f'/projects/{settings.project_id}/locations/{settings.location}'
        )

    async def _headers(self) -> dict[str, str]:
        if not self._creds.valid:
            # google-auth refresh is not coroutine-safe; serialize concurrent
            # turns and re-check under the lock so we refresh at most once.
            async with self._refresh_lock:
                if not self._creds.valid:
                    await asyncio.to_thread(self._creds.refresh, auth_requests.Request())
        return {
            'Authorization': f'Bearer {self._creds.token}',
            'Content-Type': 'application/json',
            'X-Goog-User-Project': self._settings.project_id,
            'Api-Revision': self._settings.api_revision,
        }

    async def create(  # noqa: PLR0913
        self,
        *,
        agent: str,
        content: Sequence[Mapping[str, Any]],
        environment: str | Mapping[str, Any] | None,
        previous_interaction_id: str | None,
        tools: Sequence[Mapping[str, Any]] | None,
        agent_config: Mapping[str, Any] | None = None,
        on_open: OnOpen | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """POSTs a new interaction and yields parsed SSE event objects.

        Args:
          agent: Vertex agent resource name, e.g. ``"agents/my-agent"``, or a bare
            model alias.
          content: The conversation input, already shaped as Vertex content items
            (use :class:`ContentBuilder` to convert from A2A).
          environment: Existing ``environment_id`` to reattach to, a full
            environment spec, or None to provision a new sandbox.
          previous_interaction_id: Chain this interaction onto a previous one (turn
            continuity), or None to start a new chain.
          tools: Per-interaction tool list, merged with the agent's declared tools
            by Vertex.
          agent_config: Optional per-interaction agent configuration overrides
            passed through to Vertex.
          on_open: Optional callback invoked with the live ``httpx.Response`` once
            the stream is opened; used by the executor for cancel tracking.

        Yields:
          Parsed JSON event objects from the SSE stream, terminated by
          either an ``interaction.completed`` or ``error`` event.

        Raises:
          httpx.HTTPStatusError: For HTTP >= 400 responses from Vertex.
          httpx.HTTPError: For network failures.
        """
        body: dict[str, Any] = {
            'agent': agent,
            'input': [{'type': 'user_input', 'content': list(content)}],
            'stream': True,
            'background': True,
            'store': True,
        }
        if environment is not None:
            body['environment'] = environment
        if previous_interaction_id is not None:
            body['previous_interaction_id'] = previous_interaction_id
        if tools:
            body['tools'] = list(tools)
        if agent_config:
            body['agent_config'] = dict(agent_config)
        url = f'{self._base_url}/interactions'
        async for event in self._stream('POST', url, body, on_open=on_open):
            yield event

    async def reattach(
        self,
        interaction_id: str,
        *,
        last_event_id: str | None = None,
        on_open: OnOpen | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """GETs a running interaction's SSE stream for replay/reattach.

        With *last_event_id*, the server skips already-delivered ``step.delta``
        events; framing events (``interaction.created``, ``step.start``) are
        always replayed. The consumer also accepts the legacy aliases
        (``content.delta``, ``interaction.start``, ``content.start``) for
        back-compat.
        """
        params: dict[str, str] = {'stream': 'true'}
        if last_event_id:
            params['last_event_id'] = last_event_id
        url = f'{self._base_url}/interactions/{interaction_id}'
        async for event in self._stream('GET', url, params=params, on_open=on_open):
            yield event

    async def get(self, interaction_id: str) -> dict[str, Any]:
        """GETs interaction metadata (non-streaming, for env_id salvage)."""
        url = f'{self._base_url}/interactions/{interaction_id}'
        resp = await self._http.get(url, params={'stream': 'false'}, headers=await self._headers())
        resp.raise_for_status()
        return resp.json()

    async def _stream(
        self,
        method: str,
        url: str,
        body: dict[str, Any] | None = None,
        *,
        params: Mapping[str, str] | None = None,
        on_open: OnOpen | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Opens an SSE connection and yields parsed JSON ``data:`` lines."""
        async with self._http.stream(
            method,
            url,
            params=params,
            headers=await self._headers(),
            content=json.dumps(body) if body is not None else None,
        ) as resp:
            if on_open is not None:
                on_open(resp)
            if resp.status_code >= 400:  # noqa: PLR2004
                detail = (await resp.aread()).decode('utf-8', 'replace')[:2000]
                logger.error('vertex %s %s -> %s: %s', method, url, resp.status_code, detail)
                # The body is logged for operators; surface only the status to clients.
                raise httpx.HTTPStatusError(
                    f'vertex returned HTTP {resp.status_code} {resp.reason_phrase}',
                    request=resp.request,
                    response=resp,
                )
            async for line in resp.aiter_lines():
                if not line.startswith(_SSE_DATA_PREFIX):
                    continue
                payload = line[len(_SSE_DATA_PREFIX) :]
                if payload == '[DONE]':
                    return
                try:
                    yield json.loads(payload)
                except json.JSONDecodeError:
                    logger.warning('unparsable SSE data line: %s', payload[:200])
