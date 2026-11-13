import asyncio

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING
from unittest import TestCase

import pytest

from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    DataPart,
    Message,
    MessageSendParams,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
    TextPart,
)
from agent import ReimbursementAgent, create_request_form, reimburse, return_form
from agent_executor import ReimbursementAgentExecutor
from google.adk.agents import LlmAgent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import Runner
from google.genai import types


if TYPE_CHECKING:
    from google.adk.models.llm_request import LlmRequest


class ScriptedModel(BaseLlm):
    """Provide deterministic responses without contacting a model service."""

    responses: list[types.Content]

    async def generate_content_async(
        self, llm_request: 'LlmRequest', stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        """Return the next scripted model response."""
        yield LlmResponse(content=self.responses.pop(0))


def execute_responses(monkeypatch, responses, prefix=None):
    model = ScriptedModel(model='offline', responses=responses)
    monkeypatch.setattr(
        ReimbursementAgent,
        '_build_agent',
        lambda _self: LlmAgent(
            name='reimbursement_agent',
            model=model,
            tools=[create_request_form, reimburse, return_form],
        ),
    )
    if prefix is not None:
        original_run = Runner.run_async

        async def run_with_prefix(self, **kwargs):
            async for event in original_run(self, **kwargs):
                if event.is_final_response() and event.content and event.content.parts:
                    event.content.parts.insert(0, prefix)
                yield event

        monkeypatch.setattr(Runner, 'run_async', run_with_prefix)

    async def run():
        executor = ReimbursementAgentExecutor()
        queue = EventQueue()
        context = RequestContext(
            request=MessageSendParams(
                message=Message(
                    message_id='user-message',
                    role=Role.user,
                    parts=[Part(root=TextPart(text='Reimburse this expense'))],
                )
            )
        )
        await executor.execute(context, queue)
        events = []
        while not queue.queue.empty():
            events.append(await queue.dequeue_event(no_wait=True))
            queue.task_done()
        await queue.close()
        return events

    return asyncio.run(run())


@pytest.mark.parametrize(
    ('form_first', 'prefix'),
    [
        (False, None),
        (True, None),
        (False, types.Part()),
        (False, types.Part.from_text(text='Please fill out this form.')),
    ],
    ids=['create-before-form', 'form-before-create', 'nontext-before-form', 'text-before-form'],
)
def test_final_form_requires_input(monkeypatch, form_first, prefix):
    check = TestCase()
    form_data = {'request_id': 'request_id_test', 'date': '<transaction date>'}
    calls = [
        types.Part.from_function_call(name='create_request_form', args={}),
        types.Part.from_function_call(name='return_form', args={'form_request': form_data}),
    ]
    if form_first:
        calls.reverse()
    events = execute_responses(monkeypatch, [types.Content(role='model', parts=calls)], prefix)
    statuses = [event for event in events if isinstance(event, TaskStatusUpdateEvent)]
    check.assertEqual(
        [event.status.state for event in statuses],
        [TaskState.working, TaskState.input_required],
    )
    check.assertEqual([event.final for event in statuses], [False, True])
    message = statuses[-1].status.message
    if message is None:
        pytest.fail('The form status must include a message')
    check.assertEqual(len(message.parts), 1)
    data = message.parts[0].root
    if not isinstance(data, DataPart):
        pytest.fail('The form must be a DataPart')
    check.assertEqual(data.data['type'], 'form')
    check.assertEqual(data.data['form_data'], form_data)
    check.assertFalse(any(isinstance(event, TaskArtifactUpdateEvent) for event in events))


@pytest.mark.parametrize('prefix', [None, types.Part()], ids=['text', 'nontext-before-text'])
def test_approved_reimbursement_completes_with_text(monkeypatch, prefix):
    check = TestCase()
    form = create_request_form(date='2026-10-12', amount='100', purpose='Dinner')
    text = f'Reimbursement {form["request_id"]} approved.'
    events = execute_responses(
        monkeypatch,
        [
            types.Content(
                role='model',
                parts=[
                    types.Part.from_function_call(
                        name='reimburse', args={'request_id': form['request_id']}
                    )
                ],
            ),
            types.Content(
                role='model',
                parts=[types.Part.from_text(text=text), types.Part.from_text(text='Done.')],
            ),
        ],
        prefix,
    )
    statuses = [event for event in events if isinstance(event, TaskStatusUpdateEvent)]
    check.assertEqual(
        [event.status.state for event in statuses],
        [TaskState.working, TaskState.working, TaskState.completed],
    )
    check.assertEqual([event.final for event in statuses], [False, False, True])
    artifacts = [event for event in events if isinstance(event, TaskArtifactUpdateEvent)]
    check.assertEqual(len(artifacts), 1)
    part = artifacts[0].artifact.parts[0].root
    if not isinstance(part, TextPart):
        pytest.fail('The approval artifact must be a TextPart')
    check.assertEqual(part.text, f'{text}\nDone.')
