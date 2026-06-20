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

"""Process-wide shared resources with explicit lifecycle.

A single :class:`Runtime` is constructed in ``build_app`` and passed to
``GoogleIdentityBackend``, ``ContentBuilder`` and the executor; the app
``lifespan`` closes it on shutdown. Tests construct a fresh instance per
test instead of patching module-level globals.
"""

from __future__ import annotations

import asyncio

from typing import Any

import cachetools
import httpx


_DEFAULT_TIMEOUT_S = 10
_FETCH_TIMEOUT_S = 30
_TOKENINFO_CACHE_MAXSIZE = 128
_TOKENINFO_CACHE_TTL_S = 300


class Runtime:
    """Owns shared HTTP clients and caches for one application instance."""

    def __init__(self) -> None:
        """Opens two httpx clients (general + slow-fetch) and a tokeninfo TTL cache."""
        self.http = httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S)
        self.fetch_http = httpx.AsyncClient(timeout=_FETCH_TIMEOUT_S)
        self.tokeninfo_cache: cachetools.TTLCache[str, tuple[float, dict[str, Any]]] = (
            cachetools.TTLCache(maxsize=_TOKENINFO_CACHE_MAXSIZE, ttl=_TOKENINFO_CACHE_TTL_S)
        )

    async def aclose(self) -> None:
        """Closes both HTTP clients concurrently on application shutdown."""
        await asyncio.gather(self.http.aclose(), self.fetch_http.aclose())
