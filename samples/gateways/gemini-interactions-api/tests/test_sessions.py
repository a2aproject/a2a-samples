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

# ruff: noqa: S101  # pytest-idiomatic

"""Tests for bridge.sessions."""

from __future__ import annotations

import asyncio
import datetime

from typing import TYPE_CHECKING, Any
from unittest import mock

import pytest

from bridge import sessions


if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@pytest.mark.asyncio
async def test_inmemory_round_trip() -> None:
    store = sessions.InMemorySessionStore()
    s = await store.get_or_create('k')
    assert s.env_id is None
    s.env_id = 'env-1'
    s.owner = 'u1'
    await store.persist('k', s)
    again = await store.get_or_create('k')
    assert again is s
    assert again.env_id == 'env-1'
    assert [x.env_id for x in await store.list_for('u1')] == ['env-1']
    assert await store.list_for('u2') == []


def test_build_selects_backend() -> None:
    assert isinstance(
        sessions.build(firestore_database=None, project_id='p'),
        sessions.InMemorySessionStore,
    )
    with mock.patch('google.cloud.firestore.AsyncClient') as cls:
        store = sessions.build(firestore_database='(default)', project_id='p')
    assert isinstance(store, sessions.FirestoreSessionStore)
    cls.assert_called_once_with(project='p', database='(default)')


class _FakeSnapshot:
    def __init__(self, data: dict[str, Any] | None) -> None:
        self._data = data
        self.exists = data is not None

    def to_dict(self) -> dict[str, Any] | None:
        return self._data


class _FakeDocument:
    def __init__(self, store: dict[str, dict[str, Any]], key: str) -> None:
        self._store = store
        self._key = key

    async def get(self) -> _FakeSnapshot:
        await asyncio.sleep(0)
        return _FakeSnapshot(self._store.get(self._key))

    async def set(self, data: dict[str, Any]) -> None:
        self._store[self._key] = data


class _FakeCollection:
    def __init__(self) -> None:
        self.docs: dict[str, dict[str, Any]] = {}

    def document(self, key: str) -> _FakeDocument:
        return _FakeDocument(self.docs, key)

    def where(self, *, filter: Any) -> _FakeCollection:  # noqa: A002
        self._filter_value = filter.value
        return self

    async def stream(self) -> AsyncIterator[_FakeSnapshot]:
        for d in self.docs.values():
            if d.get('owner') == self._filter_value:
                yield _FakeSnapshot(d)


@pytest.fixture
def firestore_store() -> tuple[sessions.FirestoreSessionStore, _FakeCollection]:
    coll = _FakeCollection()
    client = mock.Mock()
    client.collection.return_value = coll
    return sessions.FirestoreSessionStore(client), coll


@pytest.mark.asyncio
async def test_firestore_load_miss_creates_empty(
    firestore_store: tuple[sessions.FirestoreSessionStore, _FakeCollection],
) -> None:
    store, coll = firestore_store
    s = await store.get_or_create('ctx:agent')
    assert s.env_id is None
    assert 'ctx:agent' not in coll.docs
    assert await store.get_or_create('ctx:agent') is s


@pytest.mark.asyncio
async def test_firestore_load_hit_hydrates(
    firestore_store: tuple[sessions.FirestoreSessionStore, _FakeCollection],
) -> None:
    store, coll = firestore_store
    coll.docs['k'] = {
        'env_id': 'env-9',
        'interaction_id': 'ix-9',
        'owner': 'u1',
        'agent_key': 'code',
        'context_id': 'ctx-9',
    }
    s = await store.get_or_create('k')
    assert s.env_id == 'env-9'
    assert s.interaction_id == 'ix-9'
    assert s.context_id == 'ctx-9'


@pytest.mark.asyncio
async def test_firestore_persist_writes_doc(
    firestore_store: tuple[sessions.FirestoreSessionStore, _FakeCollection],
) -> None:
    store, coll = firestore_store
    s = await store.get_or_create('k')
    s.env_id = 'env-1'
    s.interaction_id = 'ix-1'
    s.owner = 'u1'
    s.agent_key = 'code'
    s.context_id = 'ctx-1'
    await store.persist('k', s)
    doc = coll.docs['k']
    assert doc['env_id'] == 'env-1'
    assert doc['interaction_id'] == 'ix-1'
    assert doc['owner'] == 'u1'
    assert 'updated_at' in doc


@pytest.mark.asyncio
async def test_firestore_list_for_filters_by_owner(
    firestore_store: tuple[sessions.FirestoreSessionStore, _FakeCollection],
) -> None:
    store, coll = firestore_store

    def ts(s: int) -> datetime.datetime:
        return datetime.datetime(2026, 5, 25, 0, 0, s, tzinfo=datetime.UTC)

    coll.docs = {
        'a': {'owner': 'u1', 'context_id': 'c1', 'updated_at': ts(10)},
        'b': {'owner': 'u2', 'context_id': 'c2', 'updated_at': ts(50)},
        'c': {'owner': 'u1', 'context_id': 'c3', 'updated_at': ts(30)},
        'd': {'owner': 'u1', 'context_id': 'c4'},
    }
    found = await store.list_for('u1')
    assert [s.context_id for s in found] == ['c3', 'c1', 'c4']
    assert all(s.owner == 'u1' for s in found)
    assert found[0].updated_at == ts(30)


def test_session_describe_shape() -> None:
    s = sessions.Session(env_id='e', interaction_id='i', agent_key='a', context_id='c')
    assert s.describe() == {
        'context_id': 'c',
        'agent_key': 'a',
        'env_id': 'e',
        'interaction_id': 'i',
        'updated_at': None,
    }
    s.updated_at = datetime.datetime(2026, 5, 25, 12, 0, tzinfo=datetime.UTC)
    assert s.describe()['updated_at'] == '2026-05-25T12:00:00+00:00'


@pytest.mark.asyncio
async def test_firestore_concurrent_get_or_create_same_session(
    firestore_store: tuple[sessions.FirestoreSessionStore, _FakeCollection],
) -> None:
    """Regression: an await between cache check and set must not produce two
    Sessions (and two locks) for one key."""
    store, _ = firestore_store
    s1, s2 = await asyncio.gather(store.get_or_create('k'), store.get_or_create('k'))
    assert s1 is s2
    assert s1.lock is s2.lock
