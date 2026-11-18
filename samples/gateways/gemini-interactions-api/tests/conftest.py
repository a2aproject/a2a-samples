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

# pytest-idiomatic

"""Shared pytest fixtures and helpers for the bridge test suite.

The suite is split into two layers:

* **Unit tests** exercise one module's pure logic in isolation. They use the
  lightweight fakes defined here (:class:`FakeInteractionsClient`,
  :class:`FakeUpdater`) and never touch the network or the real A2A event
  plumbing. Examples: ``test_stream.py`` (SSE event translation),
  ``test_executor.py`` (``_session_key`` / ``_vertex_overrides`` /
  ``_resolve_environment`` / ``_open_stream`` kwargs), ``test_content.py``,
  ``test_render.py``, ``test_cli.py``.
* **End-to-end tests** in ``test_e2e.py`` drive ``execute`` through the *real*
  :class:`a2a.server.tasks.TaskUpdater` and :class:`a2a.server.events.EventQueue`
  against a fake Vertex backend, then drain the queue and assert on the
  resulting ``Task`` / ``TaskStatusUpdateEvent`` protos. This is where the
  stateful executor behaviour (cancel, reattach, persist, auth-required) is
  verified against the surface the SDK actually exposes.

Six landed fixes MUST stay covered (regressions here are unacceptable):

1. cancel closes the active response, suppresses the terminal update, and
   suppresses reattach;
2. reattach forwards ``last_event_id``;
3. ID-token audience enforcement;
4. metadata-override gating via ``allow_request_overrides``;
5. SSRF guard in server-side content fetch;
6. stream cumulative-delta collapse.
"""

from __future__ import annotations

import dataclasses

from typing import TYPE_CHECKING, Any

import pytest

from a2a import types as a2a_types
from bridge import runtime as runtime_mod


if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@pytest.fixture
def runtime() -> runtime_mod.Runtime:
    """A fresh process runtime (HTTP clients + caches) per test."""
    return runtime_mod.Runtime()


# --- Current-revision SSE event builders --------------------------------------
#
# The Vertex Interactions API renamed its SSE events at Api-Revision
# 2026-05-20: ``content.*`` -> ``step.*`` and ``interaction.{start,complete}``
# -> ``interaction.{created,completed}``. Tests should emit the current names
# through these helpers; the single legacy-name regression lives in
# ``test_stream.py::test_legacy_event_names_still_handled``.


def interaction_created(
    interaction_id: str | None = 'ix-1',
    *,
    environment_id: str | None = None,
) -> dict[str, Any]:
    """Builds an ``interaction.created`` event."""
    interaction: dict[str, Any] = {}
    if interaction_id is not None:
        interaction['id'] = interaction_id
    if environment_id is not None:
        interaction['environment_id'] = environment_id
    return {'event_type': 'interaction.created', 'interaction': interaction}


def status_update(status: str) -> dict[str, Any]:
    """Builds an ``interaction.status_update`` event."""
    return {'event_type': 'interaction.status_update', 'status': status}


def step_start(step: dict[str, Any], *, index: int = 0) -> dict[str, Any]:
    """Builds a ``step.start`` event wrapping *step*."""
    return {'event_type': 'step.start', 'index': index, 'step': step}


def step_delta(kind: str, *, event_id: str | int | None = None, **fields: Any) -> dict[str, Any]:
    """Builds a ``step.delta`` event carrying a delta of *kind*."""
    event: dict[str, Any] = {
        'event_type': 'step.delta',
        'delta': {'type': kind, **fields},
    }
    if event_id is not None:
        event['event_id'] = event_id
    return event


def step_stop(*, index: int = 0) -> dict[str, Any]:
    """Builds a ``step.stop`` event."""
    return {'event_type': 'step.stop', 'index': index}


def interaction_completed(
    interaction: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Builds an ``interaction.completed`` event."""
    return {
        'event_type': 'interaction.completed',
        'interaction': interaction or {},
    }


def error_event(error: dict[str, Any]) -> dict[str, Any]:
    """Builds an ``error`` event."""
    return {'event_type': 'error', 'error': error}


class _FakeResponse:
    """Stand-in for ``httpx.Response`` registered via ``on_open``."""

    def __init__(self) -> None:
        """Records whether ``aclose`` was awaited."""
        self.closed = False

    async def aclose(self) -> None:
        """Marks the response closed; mirrors ``httpx.Response.aclose``."""
        self.closed = True


class FakeInteractionsClient:
    """Records ``create()`` kwargs and yields scripted ``events``.

    ``create_error`` (if set) is raised after the scripted ``events`` are
    exhausted, simulating a mid-stream drop. ``reattach_events`` are replayed by
    ``reattach``. ``get_result`` is returned by ``get`` so executor ``_fail``
    env-id salvage can be exercised.
    """

    def __init__(self) -> None:
        """Starts with empty scripts and no errors."""
        self.created: list[dict[str, Any]] = []
        self.reattached: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.reattach_events: list[dict[str, Any]] = []
        self.create_error: Exception | None = None
        self.get_result: dict[str, Any] = {}

    async def create(self, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        """Records *kwargs*, fires ``on_open``, then yields scripted events."""
        self.created.append(kwargs)
        on_open = kwargs.get('on_open')
        if on_open is not None:
            on_open(_FakeResponse())
        for event in self.events:
            yield event
        if self.create_error is not None:
            raise self.create_error

    async def reattach(
        self,
        interaction_id: str,
        *,
        last_event_id: str | None = None,
        on_open: Any = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Records the reattach call and replays ``reattach_events``."""
        self.reattached.append({'interaction_id': interaction_id, 'last_event_id': last_event_id})
        if on_open is not None:
            on_open(_FakeResponse())
        for event in self.reattach_events:
            yield event

    async def get(self, interaction_id: str) -> dict[str, Any]:
        """Returns the configurable ``get_result`` (for env-id salvage tests)."""
        del interaction_id
        return self.get_result

    async def aclose(self) -> None:
        """No-op shutdown hook."""
        return


@pytest.fixture
def fake_client() -> FakeInteractionsClient:
    """A fresh scripted Interactions client."""
    return FakeInteractionsClient()


class FakeUpdater:
    """Records TaskUpdater calls, mirroring the real surface.

    ``new_agent_message`` returns a real a2a ``Message`` proto (as the SDK does),
    ``update_status`` takes the same keyword surface as
    ``a2a.server.tasks.TaskUpdater.update_status``, and ``start_work`` records its
    preamble separately from the working deltas emitted by ``update_status``.
    """

    def __init__(self) -> None:
        """Starts with empty recordings."""
        self.preamble: str | None = None
        self.working: list[str] = []
        self.parts: list[list[Any]] = []
        self.states: list[Any] = []
        self.final: str | None = None
        self.final_metadata: dict[str, Any] | None = None
        self.failed_with: str | None = None
        self.cancelled_with: str | None = None

    def new_agent_message(
        self, parts: list[Any], metadata: dict[str, Any] | None = None
    ) -> a2a_types.Message:
        """Builds a real agent ``Message`` proto carrying *parts*/*metadata*."""
        return a2a_types.Message(
            role=a2a_types.Role.ROLE_AGENT,
            parts=parts,
            metadata=metadata,
        )

    @staticmethod
    def _text(message: a2a_types.Message) -> str:
        return message.parts[0].text if message.parts else ''

    async def update_status(
        self,
        state: Any,
        message: a2a_types.Message | None = None,
        timestamp: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Records a working/intermediate status update."""
        del timestamp, metadata
        self.states.append(state)
        if message is not None:
            self.working.append(self._text(message))
            self.parts.append(list(message.parts))

    async def complete(self, message: a2a_types.Message) -> None:
        """Records the final completed message and its metadata."""
        self.final = self._text(message)
        self.final_metadata = dict(message.metadata) if message.metadata else None

    async def failed(self, message: a2a_types.Message) -> None:
        """Records the failure message text."""
        self.failed_with = self._text(message)

    async def cancel(self, message: a2a_types.Message) -> None:
        """Records the cancellation message text."""
        self.cancelled_with = self._text(message)

    async def start_work(self, message: a2a_types.Message) -> None:
        """Records the ``start_work`` preamble distinctly from working deltas."""
        self.preamble = self._text(message)


@pytest.fixture
def fake_updater() -> FakeUpdater:
    """A fresh recording TaskUpdater double."""
    return FakeUpdater()


@dataclasses.dataclass
class DrainedQueue:
    """The protos drained from a real ``EventQueue`` after one turn."""

    events: list[Any]

    @property
    def task(self) -> Any | None:
        """The initial ``Task`` proto, if the turn enqueued one."""
        for event in self.events:
            if type(event).__name__ == 'Task':
                return event
        return None

    @property
    def status_events(self) -> list[Any]:
        """All ``TaskStatusUpdateEvent`` protos in arrival order."""
        return [event for event in self.events if type(event).__name__ == 'TaskStatusUpdateEvent']

    @property
    def states(self) -> list[Any]:
        """The ``status.state`` of each status update, in order."""
        return [event.status.state for event in self.status_events]

    @property
    def terminal_state(self) -> Any | None:
        """The state of the last status update, or ``None`` if there were none."""
        states = self.states
        return states[-1] if states else None

    def texts(self) -> list[str]:
        """The first-part text of every status update message."""
        out: list[str] = []
        for event in self.status_events:
            message = event.status.message
            if message.parts:
                out.append(message.parts[0].text)
        return out
