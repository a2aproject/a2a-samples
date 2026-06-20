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

"""ADC-authenticated JSON client for Google control-plane APIs."""

from __future__ import annotations

import logging
import time

from typing import TYPE_CHECKING, Any

from google import auth
from google.auth.transport import requests as auth_requests


if TYPE_CHECKING:
    from collections.abc import Sequence

    import requests


logger = logging.getLogger(__name__)

_CLOUD_PLATFORM_SCOPE = 'https://www.googleapis.com/auth/cloud-platform'
_LRO_TIMEOUT_S = 600

AGENT_UPDATE_MASK: tuple[str, ...] = (
    'description',
    'system_instruction',
    'tools',
    'base_environment',
)


class CliError(RuntimeError):
    """Raised for non-OK control-plane responses."""


class AuthedSession:
    """Thin wrapper over ``AuthorizedSession`` with LRO polling and upsert."""

    def __init__(
        self,
        *,
        endpoint: str,
        project: str,
        location: str,
        api_version: str = 'v1beta1',
    ) -> None:
        self._endpoint = endpoint.rstrip('/')
        self._api_version = api_version
        self._prefix = f'/{api_version}/projects/{project}/locations/{location}'
        creds, _ = auth.default(scopes=[_CLOUD_PLATFORM_SCOPE])
        self._http = auth_requests.AuthorizedSession(creds)
        self._http.headers['X-Goog-User-Project'] = project

    def _url(self, path: str) -> str:
        if path.startswith('http'):
            return path
        if path.startswith('/'):
            return f'{self._endpoint}{path}'
        return f'{self._endpoint}{self._prefix}/{path}'

    def request(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> requests.Response:
        """Sends an authorized request and returns the raw response."""
        return self._http.request(method, self._url(path), json=body)

    def _raise_or_json(self, resp: requests.Response, context: str) -> dict[str, Any]:
        """Raises :class:`CliError` if *resp* is not OK; returns its JSON body."""
        if not resp.ok:
            raise CliError(f'{context} -> {resp.status_code}: {resp.text[:800]}')
        return resp.json() if resp.content else {}

    def json(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        """Sends a request and returns its parsed JSON body, raising on error."""
        resp = self.request(method, path, body)
        return self._raise_or_json(resp, f'{method} {path}')

    def upsert(
        self,
        collection: str,
        resource_id: str,
        body: dict[str, Any],
        *,
        update_mask: Sequence[str],
        id_param: str | None = None,
    ) -> dict[str, Any]:
        """POSTs *body*; on 409 ALREADY_EXISTS, PATCHes with *update_mask*."""
        if id_param:
            create_path = f'{collection}?{id_param}={resource_id}'
            create_body = body
        else:
            create_path = collection
            create_body = {**body, 'id': resource_id}
        resp = self.request('POST', create_path, create_body)
        if resp.status_code == 409:  # noqa: PLR2004
            logger.info('%s/%s exists; patching', collection, resource_id)
            mask = ','.join(update_mask)
            return self.json('PATCH', f'{collection}/{resource_id}?updateMask={mask}', body)
        return self._raise_or_json(resp, f'POST {collection}')

    def upsert_and_wait(
        self,
        collection: str,
        resource_id: str,
        body: dict[str, Any],
        *,
        update_mask: Sequence[str],
        id_param: str | None = None,
    ) -> dict[str, Any]:
        """Calls :meth:`upsert`; if it returns an LRO, polls it to completion."""
        result = self.upsert(
            collection,
            resource_id,
            body,
            update_mask=update_mask,
            id_param=id_param,
        )
        name = result.get('name')
        if isinstance(name, str) and '/operations/' in name:
            return self.poll_lro(name)
        return result

    def poll_lro(self, op_name: str, interval_s: float = 3.0) -> dict[str, Any]:
        """Polls an LRO until ``done``; returns ``response`` or raises on error."""
        deadline = time.monotonic() + _LRO_TIMEOUT_S
        while True:
            op = self.json('GET', f'/{self._api_version}/{op_name}')
            if op.get('done'):
                if err := op.get('error'):
                    raise CliError(f'operation {op_name} failed: {err}')
                return op.get('response', op)
            if time.monotonic() > deadline:
                raise CliError(f'operation {op_name} timed out')
            logger.info('polling %s …', op_name)
            time.sleep(interval_s)
