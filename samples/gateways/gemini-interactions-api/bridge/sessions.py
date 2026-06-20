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

"""Session continuity stores.

A *session* maps a stable key (derived from the caller and/or A2A
``context_id``) to the two values needed to resume a Vertex Interactions
chain: ``env_id`` (which sandbox to reattach) and ``interaction_id``
(which conversation to continue). The Interactions API owns the actual
history and filesystem; the store only remembers where to point.

Two implementations share the same surface:

* :class:`InMemorySessionStore` keeps a process-local dict with idle
  eviction. Suitable for single-instance Cloud Run.
* :class:`FirestoreSessionStore` adds a Firestore document per session
  so continuity survives restarts and horizontal scale. An in-process
  dict still fronts it to hold the per-session ``asyncio.Lock``.
"""

from __future__ import annotations

import abc
import asyncio
import dataclasses
import datetime
import logging
import time

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Mapping

    from google.cloud import firestore

logger = logging.getLogger(__name__)

_COLLECTION = 'bridge_sessions'
_EPOCH = datetime.datetime.fromtimestamp(0, tz=datetime.UTC)


def _session_from_document(data: Mapping[str, Any], *, owner: str | None = None) -> Session:
    """Builds a :class:`Session` from a Firestore document mapping.

    *owner* defaults to ``data["owner"]`` when not supplied, letting callers
    that already know the owner (e.g. a filtered query) avoid re-reading it.
    """
    return Session(
        env_id=data.get('env_id'),
        interaction_id=data.get('interaction_id'),
        owner=owner if owner is not None else data.get('owner'),
        agent_key=data.get('agent_key'),
        context_id=data.get('context_id'),
        updated_at=data.get('updated_at'),
    )


def _session_to_document(session: Session) -> dict[str, Any]:
    """Returns the Firestore document mapping for *session*."""
    return {
        'env_id': session.env_id,
        'interaction_id': session.interaction_id,
        'owner': session.owner,
        'agent_key': session.agent_key,
        'context_id': session.context_id,
        'updated_at': session.updated_at,
    }


@dataclasses.dataclass
class Session:
    """Per-session cache of Vertex chain state.

    ``lock`` serialises turns on this chain (the Interactions API rejects
    concurrent interactions on the same ``previous_interaction_id``); it is
    process-local and never persisted.
    """

    env_id: str | None = None
    interaction_id: str | None = None
    owner: str | None = None
    agent_key: str | None = None
    context_id: str | None = None
    updated_at: datetime.datetime | None = None
    last_seen: float = dataclasses.field(default_factory=time.monotonic, repr=False, compare=False)
    lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock, repr=False, compare=False)

    def describe(self) -> dict[str, str | None]:
        """Returns the JSON-serialisable view used by ``GET /sessions``."""
        return {
            'context_id': self.context_id,
            'agent_key': self.agent_key,
            'env_id': self.env_id,
            'interaction_id': self.interaction_id,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SessionStore(abc.ABC):
    """Common surface for in-memory and Firestore-backed stores."""

    def __init__(self) -> None:
        self._local: dict[str, Session] = {}

    @abc.abstractmethod
    async def get_or_create(self, key: str) -> Session:
        """Returns the session for *key*, creating an empty one on first use."""

    @abc.abstractmethod
    async def persist(self, key: str, session: Session) -> None:
        """Records *session* as the latest state for *key*."""

    async def list_for(self, owner: str) -> list[Session]:
        """Returns sessions owned by *owner*.

        Ordered by most-recent activity (subclasses may sort by a persisted
        timestamp).
        """
        return sorted(
            (s for s in self._local.values() if s.owner == owner),
            key=lambda s: s.last_seen,
            reverse=True,
        )

    def start_sweeper(self, ttl_s: int) -> asyncio.Task[None] | None:
        """Starts background idle-eviction; ``None`` if handled externally."""
        del ttl_s
        return None


class InMemorySessionStore(SessionStore):
    """Process-local store with idle eviction; lost on restart."""

    async def get_or_create(self, key: str) -> Session:
        """Returns the session for *key*, creating an empty one on first use."""
        if key not in self._local:
            self._local[key] = Session()
        return self._local[key]

    async def persist(self, key: str, session: Session) -> None:
        """Stores *session* as the latest state for *key*."""
        session.last_seen = time.monotonic()
        self._local[key] = session

    def start_sweeper(self, ttl_s: int) -> asyncio.Task[None] | None:
        """Starts the idle-eviction background task."""
        return asyncio.create_task(self._sweep_loop(ttl_s))

    async def _sweep_loop(self, ttl_s: int) -> None:
        while True:
            await asyncio.sleep(min(ttl_s, 300))
            now = time.monotonic()
            expired = [k for k, s in self._local.items() if now - s.last_seen > ttl_s]
            for key in expired:
                del self._local[key]
            if expired:
                logger.info('evicted %d idle session(s)', len(expired))


class FirestoreSessionStore(SessionStore):
    """Firestore-backed store; documents live in the ``bridge_sessions`` collection.

    The in-process ``_local`` dict caches loaded sessions so the per-session
    lock is reused across turns served by the same instance. Cross-instance
    turns on the same session are not mutually excluded: if the earlier turn
    is still running the Interactions API rejects the later one (HTTP 500,
    "previous interaction not in the completed state"); if it has finished the
    chain simply branches. Either way the executor surfaces it as a retryable
    failure rather than queuing.
    """

    def __init__(self, client: firestore.AsyncClient) -> None:
        super().__init__()
        self._collection = client.collection(_COLLECTION)

    async def get_or_create(self, key: str) -> Session:
        """Returns the session for *key*, loading from Firestore on first use."""
        if (cached := self._local.get(key)) is not None:
            return cached
        snapshot = await self._collection.document(key).get()
        session = _session_from_document(snapshot.to_dict() or {})
        # A concurrent turn on the same key may have populated the cache while we
        # awaited Firestore; keep the first instance so all turns share one lock.
        return self._local.setdefault(key, session)

    async def persist(self, key: str, session: Session) -> None:
        """Writes *session* to Firestore and updates the local cache."""
        from google.cloud import firestore  # noqa: PLC0415

        session.last_seen = time.monotonic()
        self._local[key] = session
        document = _session_to_document(session)
        document['updated_at'] = firestore.SERVER_TIMESTAMP
        await self._collection.document(key).set(document)

    async def list_for(self, owner: str) -> list[Session]:
        """Returns sessions owned by *owner*, newest first.

        Unlike the base implementation (which sorts by the process-local
        ``last_seen``), this sorts by the persisted ``updated_at`` timestamp so
        the ordering is consistent across instances and restarts.
        """
        from google.cloud.firestore_v1.base_query import FieldFilter  # noqa: PLC0415

        sessions: list[Session] = []
        query = self._collection.where(filter=FieldFilter('owner', '==', owner))
        async for snapshot in query.stream():
            sessions.append(_session_from_document(snapshot.to_dict() or {}, owner=owner))  # noqa: PERF401
        sessions.sort(key=lambda s: s.updated_at or _EPOCH, reverse=True)
        return sessions


def build(*, firestore_database: str | None, project_id: str) -> SessionStore:
    """Returns a Firestore-backed store if configured, otherwise in-memory."""
    if not firestore_database:
        return InMemorySessionStore()
    from google.cloud import firestore  # noqa: PLC0415

    client = firestore.AsyncClient(project=project_id, database=firestore_database)
    logger.info('session continuity via Firestore database=%s', firestore_database)
    return FirestoreSessionStore(client)
