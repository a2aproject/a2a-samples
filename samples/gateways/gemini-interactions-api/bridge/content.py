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

"""Converts inbound A2A message parts into Vertex Interactions ``content``."""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import json
import logging
import mimetypes
import socket
import urllib.parse
import uuid

from typing import TYPE_CHECKING, Any

import httpx

from google.protobuf import json_format


if TYPE_CHECKING:
    from a2a import types as a2a_types

    from bridge import runtime as runtime_mod
    from bridge import storage


logger = logging.getLogger(__name__)

ContentItem = dict[str, Any]  # a Vertex Interactions content item

_INLINE_LIMIT_BYTES = 64 * 1024
_MAX_FETCH_BYTES = 16 * 1024 * 1024
_UPLOADS_DIR = '/workspace/uploads'
_NATIVE_MEDIA_PREFIXES = ('image', 'audio', 'video')
_DOCUMENT_MEDIA_TYPES = frozenset({'application/pdf'})
_ALLOWED_SCHEMES = frozenset({'http', 'https'})
_BLOCKED_HOSTS = frozenset({'metadata', 'metadata.google.internal'})


def _text(value: str) -> ContentItem:
    return {'type': 'text', 'text': value}


def _native_media_kind(media_type: str) -> str | None:
    """Returns the native kind (image/audio/video) for *media_type*, or None.

    These kinds may be sent inline as base64 ``data`` or staged as a signed
    ``uri``. Documents (see ``_DOCUMENT_MEDIA_TYPES``) are handled separately.
    """
    prefix = media_type.split('/', 1)[0]
    return prefix if prefix in _NATIVE_MEDIA_PREFIXES else None


def _is_public_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    return ip.is_global and not ip.is_multicast


async def _safe_fetch_target(url: str) -> tuple[str | None, str | None]:
    """Validates *url* for a server-side fetch and resolves it to one IP.

    Returns ``(ip, None)`` for an allowed URL, where *ip* is a validated public
    address the caller must connect to directly, or ``(None, reason)`` if the
    URL must not be fetched. Pinning the connection to the returned IP closes
    the DNS-rebinding / TOCTOU gap between this check and the actual request
    (the address validated here is exactly the one connected to).
    """
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return None, f'scheme {parsed.scheme!r} not allowed'
    host = (parsed.hostname or '').lower()
    if not host or host in _BLOCKED_HOSTS:
        return None, f'host {host!r} not allowed'
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as err:
        return None, f'host {host!r} did not resolve ({err})'
    addresses = [info[4][0] for info in infos]
    for address in addresses:
        if not _is_public_ip(address):
            return None, f'host {host!r} resolves to a non-public address'
    return addresses[0], None


class ContentBuilder:
    """Converter from A2A message parts to Vertex Interactions content items.

    Configured once with an optional :class:`storage.SignedUrlProvider`;
    large attachments are staged via signed URLs when a signer is present,
    inlined as base64 otherwise.
    """

    def __init__(
        self,
        runtime: runtime_mod.Runtime,
        signer: storage.SignedUrlProvider | None = None,
    ) -> None:
        """Configures a builder; *signer* enables large-attachment staging."""
        self._runtime = runtime
        self._signer = signer

    async def from_message(self, message: a2a_types.Message | None) -> list[ContentItem]:
        """Converts *message* into Interactions content items, or ``[]`` for None."""
        if message is None:
            return []
        results = await asyncio.gather(
            *(self._from_part(part) for part in message.parts),
            return_exceptions=True,
        )
        items: list[ContentItem] = []
        for result in results:
            if isinstance(result, BaseException):
                logger.warning('dropping unconvertible part: %s', result)
            elif result is not None:
                items.append(result)
        return items

    async def _from_part(self, part: a2a_types.Part) -> ContentItem | None:
        """Converts a single part to a content item, or None for unsupported kinds."""
        match part.WhichOneof('content'):
            case 'text':
                return _text(part.text)
            case 'data':
                payload = json_format.MessageToDict(part.data)
                # Fence the JSON so the model sees a clear, language-tagged boundary
                # between the payload and any surrounding instruction text.
                return _text(
                    '[structured input]\n```json\n' + json.dumps(payload, indent=2) + '\n```'
                )
            case 'raw':
                name = part.filename or 'upload'
                return await self._attachment(
                    name,
                    bytes(part.raw),
                    part.media_type or mimetypes.guess_type(name)[0] or '',
                )
            case 'url':
                name = part.filename or 'upload'
                return await self._fetch_url(
                    name,
                    part.url,
                    part.media_type or mimetypes.guess_type(name)[0] or '',
                )
        return None

    async def export_preamble(self, context_id: str) -> ContentItem | None:
        """Returns the per-turn ``[artifact-export]`` instruction, if enabled."""
        if self._signer is None:
            return None
        blob = f'outputs/{context_id}/{uuid.uuid4().hex[:8]}'
        pair = await self._signer.signed_pair(blob)
        if pair is None:
            return None
        put_url, get_url = pair
        return _text(
            '[artifact-export] To let the user download a file you produce, '
            'upload it (tar/zip first if multiple) with:\n'
            f"  curl -fsS -X PUT -T <path> '{put_url}'\n"
            'then print this download link on its own line:\n'
            f'  {get_url}'
        )

    async def _attachment(self, name: str, data: bytes, media_type: str) -> ContentItem:
        media_kind = _native_media_kind(media_type)
        if len(data) > _INLINE_LIMIT_BYTES:
            if self._signer is not None:
                return await self._staged_attachment(name, data, media_type, media_kind)
            logger.warning(
                'inlining %d-byte attachment %r as base64; configure UPLOAD_BUCKET',
                len(data),
                name,
            )
        encoded = base64.b64encode(data).decode('ascii')
        if media_kind:
            return {'type': media_kind, 'data': encoded, 'mime_type': media_type}
        if media_type in _DOCUMENT_MEDIA_TYPES:
            # PDFs ingest natively as a document; the model reads them directly
            # rather than base64-decoding into the sandbox.
            return {'type': 'document', 'data': encoded, 'mime_type': media_type}
        return _text(
            f'[attachment] {name} (base64, {len(data)} bytes):\n{encoded}\n'
            f'Decode and write it to {_UPLOADS_DIR}/{name} before proceeding.'
        )

    async def _staged_attachment(
        self, name: str, data: bytes, media_type: str, media_kind: str | None
    ) -> ContentItem:
        assert self._signer is not None  # noqa: S101
        blob = f'uploads/{uuid.uuid4().hex}-{name}'
        await self._signer.upload(blob, data)
        url = await self._signer.signed_get(blob)
        if media_kind:
            return {'type': media_kind, 'uri': url, 'mime_type': media_type}
        # Documents and unknown types are fetched into the sandbox by the model.
        # The native document `uri` reference shape is not yet validated, so large
        # documents deliberately stay on this fetch-into-sandbox path.
        return _text(
            f'[attachment] {name} staged in GCS. Fetch it with:\n'
            f'  mkdir -p {_UPLOADS_DIR} && '
            f"curl -fsSL -o {_UPLOADS_DIR}/{name} '{url}'"
        )

    def _pinned_request(self, url: str, ip: str) -> httpx.Request:
        """Builds a GET request pinned to the validated *ip*.

        The connection targets *ip* directly so the hostname cannot be
        re-resolved to an internal address after validation. The original host
        is preserved in the ``Host`` header and, for HTTPS, as the TLS SNI and
        certificate-verification name.
        """
        parsed = urllib.parse.urlsplit(url)
        host = parsed.hostname or ''
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        netloc = f'[{ip}]:{port}' if ':' in ip else f'{ip}:{port}'
        pinned = urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, ''))
        host_header = parsed.netloc.rsplit('@', 1)[-1]
        request = self._runtime.fetch_http.build_request(
            'GET', pinned, headers={'Host': host_header}
        )
        if parsed.scheme == 'https':
            request.extensions['sni_hostname'] = host
        return request

    async def _fetch_url(self, name: str, url: str, media_type: str) -> ContentItem:
        ip, reason = await _safe_fetch_target(url)
        if ip is None:
            logger.warning('refusing to fetch %s: %s', url, reason)
            return _text(f'[attachment] {name}: refused to fetch {url} ({reason}).')
        request = self._pinned_request(url, ip)
        chunks: list[bytes] = []
        total = 0
        try:
            resp = await self._runtime.fetch_http.send(request, stream=True)
            try:
                resp.raise_for_status()
                media_type = media_type or (resp.headers.get('content-type') or '').split(';', 1)[0]
                async for chunk in resp.aiter_bytes(64 * 1024):
                    total += len(chunk)
                    if total > _MAX_FETCH_BYTES:
                        return _text(f'[attachment] {name}: too large (> {_MAX_FETCH_BYTES} bytes)')
                    chunks.append(chunk)
            finally:
                await resp.aclose()
        except httpx.HTTPError as err:
            logger.warning('attachment fetch failed for %s: %s', url, err)
            return _text(f'[attachment] {name} could not be fetched from {url}.')
        return await self._attachment(name, b''.join(chunks), media_type)
