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

"""GCS helper for V4 signed URLs and uploads.

Signed URLs are produced via the IAM ``signBlob`` API (no key file required),
so the runtime service account must hold ``roles/iam.serviceAccountTokenCreator``
on itself.
"""

from __future__ import annotations

import asyncio
import datetime
import logging

import google.cloud.storage as gcs
import httpx

from google.api_core import exceptions as gcp_exceptions
from google.auth import exceptions as auth_exceptions
from google.auth.transport import requests as auth_requests

from bridge import auth


logger = logging.getLogger(__name__)

_SIGNED_URL_TTL = datetime.timedelta(hours=1)
_METADATA_SA_EMAIL = (
    'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email'
)


class SignedUrlProvider:
    """V4 signed-URL minter and blob writer for one GCS bucket.

    Sync GCS calls run in a thread.
    """

    def __init__(self, bucket_name: str) -> None:
        """Targets *bucket_name*; resolves the SA email for V4 signing eagerly."""
        self._bucket_name = bucket_name
        self._client = gcs.Client()
        self._creds = auth.adc_credentials()
        self._refresh()
        self._sa_email = self._resolve_sa_email()

    def _resolve_sa_email(self) -> str | None:
        email = getattr(self._creds, 'service_account_email', None)
        if email not in (None, 'default'):
            return email
        # Cloud Run metadata creds report "default" until queried explicitly.
        try:
            resp = httpx.get(
                _METADATA_SA_EMAIL,
                headers={'Metadata-Flavor': 'Google'},
                timeout=2,
            )
        except httpx.HTTPError as err:
            logger.warning('metadata server unreachable; signed URLs disabled (%s)', err)
            return None
        email = resp.text.strip()
        if '@' not in email or len(email) > 200:  # noqa: PLR2004
            logger.warning('metadata returned invalid SA email: %r', email[:100])
            return None
        return email

    def _refresh(self) -> None:
        if not self._creds.valid:
            self._creds.refresh(auth_requests.Request())

    def _blob(self, name: str) -> gcs.Blob:
        return self._client.bucket(self._bucket_name).blob(name)

    def _sign(self, name: str, method: str) -> str:
        self._refresh()
        return self._blob(name).generate_signed_url(
            version='v4',
            method=method,
            expiration=_SIGNED_URL_TTL,
            service_account_email=self._sa_email,
            access_token=self._creds.token,
        )

    async def signed_pair(self, name: str) -> tuple[str, str] | None:
        """Returns (PUT url, GET url) for *name*, or None on auth failure."""
        try:
            return await asyncio.to_thread(
                lambda: (self._sign(name, 'PUT'), self._sign(name, 'GET'))
            )
        except (
            auth_exceptions.GoogleAuthError,
            gcp_exceptions.GoogleAPIError,
        ) as err:
            logger.warning('signed-url generation failed: %s', err)
            return None

    async def signed_get(self, name: str) -> str:
        """Returns a signed GET URL for *name*."""
        return await asyncio.to_thread(self._sign, name, 'GET')

    async def upload(self, name: str, data: bytes) -> None:
        """Uploads *data* to *name* in the configured bucket."""
        await asyncio.to_thread(self._blob(name).upload_from_string, data)
