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

# ruff: noqa: S101, SLF001, PLR0913  # pytest-idiomatic

"""Tests for bridge.content."""

import base64
import json

from unittest import mock

import httpx
import pytest

from a2a import types as a2a_types
from bridge import content
from bridge import runtime as runtime_mod
from google.protobuf import json_format


class _FakeSigner:
    def __init__(self) -> None:
        self.uploaded: dict[str, bytes] = {}

    async def signed_pair(self, name: str) -> tuple[str, str]:
        return f'https://put/{name}', f'https://get/{name}'

    async def signed_get(self, name: str) -> str:
        return f'https://get/{name}'

    async def upload(self, name: str, data: bytes) -> None:
        self.uploaded[name] = data


@pytest.mark.asyncio
async def test_small_attachment_inlined_as_base64(
    runtime: runtime_mod.Runtime,
) -> None:
    builder = content.ContentBuilder(runtime, signer=None)
    item = await builder._attachment('a.bin', b'\x00\x01', '')
    assert item['type'] == 'text'
    assert base64.b64encode(b'\x00\x01').decode() in item['text']
    assert '/workspace/uploads/a.bin' in item['text']


@pytest.mark.asyncio
async def test_native_image_inlined_as_typed_content(
    runtime: runtime_mod.Runtime,
) -> None:
    builder = content.ContentBuilder(runtime, signer=None)
    item = await builder._attachment('a.png', b'\x89PNG', 'image/png')
    assert item == {
        'type': 'image',
        'data': base64.b64encode(b'\x89PNG').decode(),
        'mime_type': 'image/png',
    }


@pytest.mark.asyncio
async def test_pdf_inlined_as_native_document(
    runtime: runtime_mod.Runtime,
) -> None:
    builder = content.ContentBuilder(runtime, signer=None)
    item = await builder._attachment('doc.pdf', b'%PDF-1.4', 'application/pdf')
    assert item == {
        'type': 'document',
        'data': base64.b64encode(b'%PDF-1.4').decode(),
        'mime_type': 'application/pdf',
    }


@pytest.mark.asyncio
async def test_large_attachment_staged_via_signed_url(
    runtime: runtime_mod.Runtime,
) -> None:
    signer = _FakeSigner()
    builder = content.ContentBuilder(runtime, signer=signer)
    big = b'x' * (content._INLINE_LIMIT_BYTES + 1)
    item = await builder._attachment('big.bin', big, 'application/zip')
    assert 'curl -fsSL -o /workspace/uploads/big.bin' in item['text']
    assert any(v == big for v in signer.uploaded.values())


@pytest.mark.asyncio
async def test_large_native_image_staged_as_uri(
    runtime: runtime_mod.Runtime,
) -> None:
    signer = _FakeSigner()
    builder = content.ContentBuilder(runtime, signer=signer)
    big = b'x' * (content._INLINE_LIMIT_BYTES + 1)
    item = await builder._attachment('big.jpg', big, 'image/jpeg')
    assert item['type'] == 'image'
    assert item['mime_type'] == 'image/jpeg'
    assert item['uri'].startswith('https://get/uploads/')


@pytest.mark.asyncio
async def test_export_preamble_requires_signer(
    runtime: runtime_mod.Runtime,
) -> None:
    # Without a signer the preamble is disabled (no upload destination).
    assert await content.ContentBuilder(runtime, signer=None).export_preamble('ctx') is None
    # With a signer it embeds both the signed PUT and GET URLs.
    item = await content.ContentBuilder(runtime, signer=_FakeSigner()).export_preamble('ctx-1')
    assert item is not None
    assert 'https://put/outputs/ctx-1/' in item['text']
    assert 'https://get/outputs/ctx-1/' in item['text']


@pytest.mark.asyncio
async def test_from_message_maps_text_and_data(
    runtime: runtime_mod.Runtime,
) -> None:
    msg = json_format.ParseDict(
        {
            'parts': [
                {'text': 'hello'},
                {'data': {'rows': [{'a': 1}], 'count': 1}},
            ]
        },
        a2a_types.Message(),
    )
    builder = content.ContentBuilder(runtime, signer=None)
    items = await builder.from_message(msg)
    assert items[0] == {'type': 'text', 'text': 'hello'}
    assert items[1]['text'].startswith('[structured input]\n```json\n')
    fenced = items[1]['text'].removeprefix('[structured input]\n```json\n')
    payload = json.loads(fenced.removesuffix('\n```'))
    assert payload == {'rows': [{'a': 1}], 'count': 1}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'url',
    [
        'file:///etc/passwd',
        'gopher://x',
        'http://metadata.google.internal/computeMetadata/v1/',
        'http://metadata/computeMetadata/v1/',
        'http://169.254.169.254/',
        'http://127.0.0.1:8080/',
        'http://[::1]/',
        'http://10.0.0.5/',
    ],
)
async def test_reject_unsafe_url_blocks_internal_targets(url: str) -> None:
    reason = await content._reject_unsafe_url(url)
    assert reason is not None


def _mock_transport(body: bytes, status: int = 200) -> httpx.AsyncClient:
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=body, headers={'content-type': 'image/png'})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_fetch_url_refused_target_returns_text(
    runtime: runtime_mod.Runtime,
) -> None:
    """SSRF refusal: the guard fires before any transport call is made."""
    builder = content.ContentBuilder(runtime, signer=None)
    item = await builder._fetch_url('a', 'http://127.0.0.1/', '')
    assert item['type'] == 'text'
    assert 'refused to fetch' in item['text']


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('body', 'status', 'expected_type', 'expected_substr'),
    [
        # Allowed fetch converts through _attachment to a typed native item.
        (b'\x89PNG', 200, 'image', None),
        # Oversized body is truncated to a text refusal.
        (b'x' * (content._MAX_FETCH_BYTES + 1), 200, 'text', 'too large'),
        # HTTP error falls back to a text placeholder.
        (b'', 500, 'text', 'could not be fetched'),
    ],
)
async def test_fetch_url_through_transport(
    runtime: runtime_mod.Runtime,
    monkeypatch: pytest.MonkeyPatch,
    body: bytes,
    status: int,
    expected_type: str,
    expected_substr: str | None,
) -> None:
    monkeypatch.setattr(content, '_reject_unsafe_url', mock.AsyncMock(return_value=None))
    runtime.fetch_http = _mock_transport(body, status=status)
    builder = content.ContentBuilder(runtime, signer=None)
    item = await builder._fetch_url('a.png', 'https://x/a.png', '')
    assert item['type'] == expected_type
    if expected_substr is not None:
        assert expected_substr in item['text']
    if expected_type == 'image':
        assert item['mime_type'] == 'image/png'
