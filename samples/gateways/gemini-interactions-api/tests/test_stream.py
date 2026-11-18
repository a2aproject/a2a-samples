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

# ruff: noqa: S101, SLF001, PLR2004  # pytest-idiomatic

"""Unit tests for ``bridge.stream`` (SSE -> A2A status translation).

Events are built with the current-revision helpers in ``conftest`` (``step.*`` /
``interaction.{created,completed}``). Exactly one test
(``test_legacy_event_names_still_handled``) exercises the pre-2026-05-20 names
to confirm the consumer still accepts old streams.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from a2a import types as a2a_types
from bridge import sessions, stream
from google.protobuf import json_format

from tests import conftest


if TYPE_CHECKING:
    from collections.abc import AsyncIterator


async def _feed(events: list[dict[str, Any]]) -> AsyncIterator[dict[str, Any]]:
    for event in events:
        yield event


def _consumer(
    fake_updater: conftest.FakeUpdater,
    session: sessions.Session | None = None,
) -> stream.StreamConsumer:
    return stream.StreamConsumer(session or sessions.Session(), fake_updater)


@pytest.mark.asyncio
async def test_final_excludes_pre_tool_narration(
    fake_updater: conftest.FakeUpdater,
) -> None:
    """Regression: pre-tool text must not be re-sent in the final message."""
    events = [
        conftest.interaction_created('ix-1'),
        conftest.step_delta('text', text='Let me check that. '),
        conftest.step_delta('function_call', name='run', arguments={'CommandLine': 'ls'}),
        conftest.step_delta('function_result', result={'Output': '[STDOUT]\nfile.txt'}),
        conftest.step_delta('text', text='Found '),
        conftest.step_delta('text', text='one file.'),
        conftest.step_stop(),
        conftest.interaction_completed({'id': 'ix-1'}),
    ]
    consumer = _consumer(fake_updater)
    await consumer.run(_feed(events))

    assert consumer.terminal == 'completed'
    assert fake_updater.final == 'Found one file.'
    assert 'Let me check that. ' in fake_updater.working
    assert '⏵ run: `ls`' in fake_updater.working


@pytest.mark.asyncio
async def test_final_prefers_interaction_output(
    fake_updater: conftest.FakeUpdater,
) -> None:
    events = [
        conftest.step_delta('text', text='streamed'),
        conftest.interaction_completed(
            {
                'id': 'ix-2',
                'output': [{'content': [{'type': 'text', 'text': 'authoritative'}]}],
                'usage': {'input_tokens': 1},
            }
        ),
    ]
    consumer = _consumer(fake_updater)
    await consumer.run(_feed(events))

    assert fake_updater.final == 'authoritative'
    assert fake_updater.final_metadata == {'usage': {'input_tokens': 1}}


@pytest.mark.asyncio
async def test_flush_drops_trailing_cumulative_delta(
    fake_updater: conftest.FakeUpdater,
) -> None:
    """Regression: Vertex re-sends pre-tool narration as one full final delta.

    Captured live 2026-05-26 against ``Api-Revision: 2026-05-20``: each
    ``model_output`` block that precedes a ``function_call`` streams N
    incremental ``text`` deltas followed by one delta whose text equals the
    concatenation of the previous N. Without collapsing, the flushed working
    update doubles the narration ("I will run lsI will run ls").
    """
    events = [
        conftest.step_start({'type': 'model_output'}, index=0),
        conftest.step_delta('text', text='I will '),
        conftest.step_delta('text', text='run ls.'),
        conftest.step_delta('text', text='I will run ls.'),
        conftest.step_stop(index=0),
        conftest.step_start({'type': 'function_call', 'name': 'run', 'arguments': {}}, index=1),
        conftest.step_stop(index=1),
        conftest.step_delta('text', text='Found '),
        conftest.step_delta('text', text='one file.'),
        conftest.step_stop(index=2),
        conftest.interaction_completed(),
    ]
    consumer = _consumer(fake_updater)
    await consumer.run(_feed(events))

    assert fake_updater.working.count('I will run ls.') == 1
    assert 'I will run ls.I will run ls.' not in fake_updater.working
    assert fake_updater.final == 'Found one file.'


@pytest.mark.asyncio
async def test_reattach_dedupes_by_event_id(
    fake_updater: conftest.FakeUpdater,
) -> None:
    consumer = _consumer(fake_updater)
    await consumer.run(
        _feed(
            [
                conftest.step_delta('text', event_id=1, text='a'),
                conftest.step_delta('text', event_id=2, text='b'),
            ]
        )
    )
    # Simulated reattach replays event 2 then continues.
    await consumer.run(
        _feed(
            [
                conftest.step_delta('text', event_id=2, text='b'),
                conftest.step_delta('text', event_id=3, text='c'),
                conftest.interaction_completed(),
            ]
        )
    )
    assert fake_updater.final == 'abc'


@pytest.mark.asyncio
async def test_legacy_event_names_still_handled(
    fake_updater: conftest.FakeUpdater,
) -> None:
    """The consumer must still accept the pre-2026-05-20 event names.

    ``step.*`` was ``content.*``; ``interaction.{created,completed}`` was
    ``interaction.{start,complete}``. Only this test uses the legacy names; all
    others go through the current-revision builders.
    """
    session = sessions.Session()
    events = [
        {'event_type': 'interaction.start', 'interaction': {'id': 'ix-s'}},
        {
            'event_type': 'content.start',
            'content': {'type': 'function_call', 'name': 'run', 'arguments': {}},
        },
        {'event_type': 'content.delta', 'delta': {'type': 'text', 'text': 'rdy'}},
        {'event_type': 'content.stop'},
        {
            'event_type': 'interaction.complete',
            'interaction': {'id': 'ix-s', 'environment_id': 'env-s'},
        },
    ]
    consumer = _consumer(fake_updater, session)
    await consumer.run(_feed(events))

    assert consumer.terminal == 'completed'
    assert session.interaction_id == 'ix-s'
    assert session.env_id == 'env-s'
    assert fake_updater.final == 'rdy'
    assert any(w.startswith('⏵ run') for w in fake_updater.working)


@pytest.mark.asyncio
async def test_error_event_records_message(
    fake_updater: conftest.FakeUpdater,
) -> None:
    consumer = _consumer(fake_updater)
    await consumer.run(_feed([conftest.error_event({'message': 'boom'})]))
    assert consumer.error == 'boom'
    assert consumer.terminal == 'failed'
    assert fake_updater.final is None


@pytest.mark.asyncio
async def test_citations_appended_to_final(
    fake_updater: conftest.FakeUpdater,
) -> None:
    events = [
        conftest.step_delta('text', text='answer'),
        conftest.interaction_completed({'annotations': [{'url': 'https://x', 'title': 'X'}]}),
    ]
    consumer = _consumer(fake_updater)
    await consumer.run(_feed(events))
    assert fake_updater.final is not None
    assert fake_updater.final.startswith('answer\n\n**Sources**')
    assert fake_updater.final_metadata is not None
    assert 'annotations' in fake_updater.final_metadata


@pytest.mark.asyncio
async def test_function_result_emits_data_part(
    fake_updater: conftest.FakeUpdater,
) -> None:
    consumer = _consumer(fake_updater)
    await consumer.run(
        _feed([conftest.step_delta('function_result', result={'Output': 'rows', 'n': 2})])
    )
    parts = fake_updater.parts[-1]
    assert len(parts) == 2
    assert parts[0].text == '```\nrows\n```'
    data = json_format.MessageToDict(parts[1])['data']
    assert data == {'Output': 'rows', 'n': 2}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'error_info',
    [
        {'code': 'unauthenticated', 'tool': 'bigquery'},
        {'status': 'UNAUTHENTICATED', 'tool': 'bigquery'},
    ],
)
async def test_error_unauthenticated_emits_auth_required(
    fake_updater: conftest.FakeUpdater, error_info: dict[str, Any]
) -> None:
    consumer = _consumer(fake_updater)
    await consumer.run(_feed([conftest.error_event(error_info)]))
    assert consumer.terminal == 'auth_required'
    assert consumer.error is None
    assert fake_updater.states[-1] == a2a_types.TaskState.TASK_STATE_AUTH_REQUIRED
    assert 'bigquery' in fake_updater.working[-1]


@pytest.mark.asyncio
@pytest.mark.parametrize('status', ['failed', 'incomplete', 'budget_exceeded'])
async def test_status_update_failure_is_terminal(
    fake_updater: conftest.FakeUpdater, status: str
) -> None:
    consumer = _consumer(fake_updater)
    await consumer.run(
        _feed(
            [
                conftest.step_delta('text', text='partial'),
                conftest.status_update(status),
            ]
        )
    )
    assert consumer.terminal == 'failed'
    assert consumer.error is not None
    assert status in consumer.error
    assert fake_updater.final is None


@pytest.mark.asyncio
async def test_error_403_records_failure(
    fake_updater: conftest.FakeUpdater,
) -> None:
    consumer = _consumer(fake_updater)
    await consumer.run(
        _feed([conftest.error_event({'status': 'PERMISSION_DENIED', 'tool': 'drive'})])
    )
    assert consumer.terminal == 'failed'
    assert consumer.error is not None
    assert 'permission' in consumer.error


@pytest.mark.asyncio
async def test_status_requires_action_emits_input_required(
    fake_updater: conftest.FakeUpdater,
) -> None:
    consumer = _consumer(fake_updater)
    await consumer.run(
        _feed(
            [
                conftest.step_delta('text', text='which table?'),
                conftest.step_stop(),
                conftest.status_update('requires_action'),
            ]
        )
    )
    assert consumer.terminal == 'input_required'
    assert fake_updater.states[-1] == (a2a_types.TaskState.TASK_STATE_INPUT_REQUIRED)
    assert 'which table?' in fake_updater.working[-1]


@pytest.mark.asyncio
async def test_last_event_id_tracks_latest_delta(
    fake_updater: conftest.FakeUpdater,
) -> None:
    consumer = _consumer(fake_updater)
    await consumer.run(
        _feed(
            [
                conftest.step_delta('text', event_id='v1_1', text='a'),
                conftest.step_delta('text', event_id='v1_2', text='b'),
            ]
        )
    )
    assert consumer.last_event_id == 'v1_2'
    await consumer.run(_feed([conftest.step_delta('text', event_id='v1_2', text='b')]))
    assert consumer._text_buffer == ['a', 'b']


@pytest.mark.asyncio
async def test_text_annotation_collected_into_metadata(
    fake_updater: conftest.FakeUpdater,
) -> None:
    consumer = _consumer(fake_updater)
    await consumer.run(
        _feed(
            [
                conftest.step_delta('text', text='answer'),
                conftest.step_delta(
                    'text_annotation',
                    annotations=[{'type': 'url_citation', 'url': 'https://x'}],
                ),
                conftest.interaction_completed(),
            ]
        )
    )
    assert fake_updater.final_metadata is not None
    annotations = fake_updater.final_metadata['annotations']
    assert annotations[0]['url'] == 'https://x'
