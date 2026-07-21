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

"""Consumes the Vertex Interactions SSE stream and emits A2A status updates."""

from __future__ import annotations

import logging

from collections.abc import AsyncIterator, Mapping
from typing import TYPE_CHECKING, Any, Literal

from a2a import types as a2a_types
from google.protobuf import json_format

from bridge import render, sessions


if TYPE_CHECKING:
    from a2a.server import tasks as a2a_tasks


logger = logging.getLogger(__name__)

_UNAUTHENTICATED_CODES = frozenset({'unauthenticated', 'UNAUTHENTICATED'})
_PERMISSION_DENIED_CODES = frozenset({'permission_denied', 'PERMISSION_DENIED'})
_FAILED_STATUSES = frozenset({'failed', 'incomplete', 'budget_exceeded'})


def _parts(text: str, data: Mapping[str, Any] | None = None) -> list[a2a_types.Part]:
    parts = [a2a_types.Part(text=text)]
    if data is not None:
        parts.append(json_format.ParseDict({'data': dict(data)}, a2a_types.Part()))
    return parts


def _final_text(interaction: Mapping[str, Any]) -> str:
    """Returns the last assistant text block from a completed interaction."""
    output = interaction.get('output') or []
    if not output:
        return ''
    pieces = [
        item.get('text', '')
        for item in output[-1].get('content') or []
        if item.get('type') == 'text'
    ]
    return ''.join(pieces)


def _collect_annotations(
    interaction: Mapping[str, Any],
) -> list[dict[str, Any]]:
    top = interaction.get('annotations')
    if top:
        return list(top)
    found: list[dict[str, Any]] = []
    for item in interaction.get('output') or []:
        for part in item.get('content') or []:
            found.extend(part.get('annotations') or [])
    return found


class StreamConsumer:
    """Translates Interactions SSE events into A2A ``TaskUpdater`` calls.

    State persists across ``run`` invocations so the executor can reattach to
    a dropped stream without replaying already-seen deltas.
    """

    def __init__(
        self,
        session: sessions.Session,
        updater: a2a_tasks.TaskUpdater,
    ) -> None:
        """Binds to *session* (mutated as events arrive) and *updater* (A2A sink)."""
        self._session = session
        self._updater = updater
        self._seen: set[str] = set()
        self._text_buffer: list[str] = []
        self._annotations: list[dict[str, Any]] = []
        self._last_flushed_text: str = ''
        self.last_event_id: str | None = None
        self.terminal: Literal['completed', 'auth_required', 'input_required', 'failed'] | None = (
            None
        )
        self.error: str | None = None

    async def run(self, events: AsyncIterator[dict[str, Any]]) -> None:
        """Dispatches *events* until exhausted or a terminal event arrives."""
        async for event in events:
            match event.get('event_type'):
                case 'interaction.start' | 'interaction.created':
                    await self._on_interaction_start(event)
                case 'interaction.status_update':
                    await self._on_status_update(event)
                case 'content.start' | 'step.start':
                    await self._on_content_start(event)
                case 'content.delta' | 'step.delta':
                    await self._on_content_delta(event)
                case 'content.stop' | 'step.stop':
                    await self._flush()
                case 'interaction.complete' | 'interaction.completed':
                    await self._on_interaction_complete(event)
                case 'error':
                    await self._on_error(event)
                case 'done' | None:
                    pass
                case _ as unknown:
                    logger.debug('unknown event_type: %s', unknown)
            if self.terminal is not None:
                return

    async def _working(self, text: str, data: Mapping[str, Any] | None = None) -> None:
        await self._updater.update_status(
            a2a_types.TaskState.TASK_STATE_WORKING,
            message=self._updater.new_agent_message(_parts(text, data)),
        )

    async def _flush(self) -> None:
        """Emits buffered text as a WORKING update; no-op when the buffer is empty."""
        if not self._text_buffer:
            return
        chunks, self._text_buffer = self._text_buffer, []
        # Vertex re-sends pre-tool narration as one cumulative trailing delta.
        if len(chunks) > 1 and chunks[-1] == ''.join(chunks[:-1]):
            self._last_flushed_text = chunks[-1]
        else:
            self._last_flushed_text = ''.join(chunks)
        await self._working(self._last_flushed_text)

    async def _on_interaction_start(self, event: Mapping[str, Any]) -> None:
        interaction = event.get('interaction') or {}
        self._session.interaction_id = interaction.get('id')
        env_id = interaction.get('environment_id') or interaction.get('environment')
        if isinstance(env_id, str):
            self._session.env_id = env_id
        await self._working('sandbox attached')

    async def _on_status_update(self, event: Mapping[str, Any]) -> None:
        status = event.get('status')
        if status == 'requires_action':
            await self._flush()
            await self._updater.update_status(
                a2a_types.TaskState.TASK_STATE_INPUT_REQUIRED,
                message=self._updater.new_agent_message(
                    _parts(self._last_flushed_text or 'the agent needs your input')
                ),
            )
            self.terminal = 'input_required'
        elif status in _FAILED_STATUSES:
            self.error = f'interaction status: {status}'
            self.terminal = 'failed'

    async def _on_content_start(self, event: Mapping[str, Any]) -> None:
        content = event.get('step') or event.get('content') or {}
        if str(content.get('type') or '').endswith('_call'):
            await self._flush()
            await self._working(render.function_call(content))

    async def _on_content_delta(self, event: Mapping[str, Any]) -> None:
        event_id = event.get('event_id')
        if event_id is not None:
            key = str(event_id)
            if key in self._seen:
                return
            self._seen.add(key)
            self.last_event_id = key
        delta = event.get('delta') or {}
        delta_type = delta.get('type') or ''
        match delta_type:
            case 'text':
                if text_chunk := delta.get('text'):
                    self._text_buffer.append(text_chunk)
            case 'text_annotation':
                self._annotations.extend(delta.get('annotations') or [])
            case 'thought' | 'thought_summary':
                if text_chunk := delta.get('text'):
                    await self._working(f'[thinking] {text_chunk}')
            case _ if delta_type.endswith('_call'):
                await self._flush()
                await self._working(render.function_call(delta))
            case _ if delta_type.endswith('_result'):
                await self._flush()
                if rendered := render.function_result(delta):
                    result = delta.get('result')
                    await self._working(rendered, result if isinstance(result, Mapping) else None)

    async def _on_interaction_complete(self, event: Mapping[str, Any]) -> None:
        interaction = event.get('interaction') or {}
        self._session.interaction_id = interaction.get('id') or self._session.interaction_id
        if env_id := interaction.get('environment_id'):
            self._session.env_id = env_id
        final = (
            _final_text(interaction)
            or ''.join(self._text_buffer)
            or self._last_flushed_text
            or 'done'
        )
        annotations = self._annotations + _collect_annotations(interaction)
        if cited := render.citations(annotations):
            final = f'{final}\n\n{cited}'
        metadata: dict[str, Any] = {}
        if usage := interaction.get('usage'):
            metadata['usage'] = usage
        if annotations:
            metadata['annotations'] = annotations
        await self._updater.complete(
            message=self._updater.new_agent_message(_parts(final), metadata=metadata or None)
        )
        self.terminal = 'completed'

    async def _on_error(self, event: Mapping[str, Any]) -> None:
        error_info = event.get('error') or {}
        code = error_info.get('code')
        status = error_info.get('status')
        tool = error_info.get('tool') or 'the tool'
        if code in _UNAUTHENTICATED_CODES or status in _UNAUTHENTICATED_CODES:
            await self._updater.update_status(
                a2a_types.TaskState.TASK_STATE_AUTH_REQUIRED,
                message=self._updater.new_agent_message(
                    _parts(
                        f'The {tool} server rejected your credentials; '
                        'retry with a fresh access token.'
                    )
                ),
            )
            self.terminal = 'auth_required'
            return
        if code in _PERMISSION_DENIED_CODES or status in _PERMISSION_DENIED_CODES:
            self.error = f"You don't have permission on the resource {tool} tried to access."
        else:
            self.error = error_info.get('message') or 'unknown error'
        self.terminal = 'failed'
