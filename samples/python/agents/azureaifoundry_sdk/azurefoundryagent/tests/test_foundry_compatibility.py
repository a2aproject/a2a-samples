import importlib
import os
import runpy
import unittest

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx

from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.helpers import new_data_part, new_text_message
from a2a.server.agent_execution import RequestContext
from a2a.server.context import ServerCallContext
from a2a.server.events import EventQueue
from a2a.types import AgentCard, Part, Role, SendMessageRequest, Task, TaskState
from a2a.utils.errors import InvalidParamsError, TaskNotCancelableError
from sse_starlette.sse import AppStatus


SAMPLE = Path(__file__).resolve().parents[1]
BASE_URL = 'http://testserver:10007'


class RecordingQueue(EventQueue):
    def __init__(self):
        self.events = []

    async def enqueue_event(self, event):
        self.events.append(event)


def build_app():
    module = runpy.run_path(str(SAMPLE / '__main__.py'), run_name='foundry_test_server')
    environment = {
        'AZURE_AI_FOUNDRY_PROJECT_ENDPOINT': 'https://foundry.example/api/projects/test',
        'AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME': 'test-deployment',
    }
    with patch.dict(os.environ, environment), patch('uvicorn.run') as server:
        module['main'].main(args=['--host', 'testserver', '--port', '10007'], standalone_mode=False)
    return server.call_args.args[0]


def make_context(parts=None, task_id='test-task', context_id='test-context'):
    return RequestContext(
        call_context=ServerCallContext(),
        task_id=task_id,
        context_id=context_id,
        request=SendMessageRequest(
            message=new_text_message('Hello', role=Role.ROLE_USER)
            if parts is None
            else {'role': Role.ROLE_USER, 'parts': parts, 'message_id': task_id},
        ),
    )


class FoundryCompatibilityTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # sse-starlette 2.x shares its shutdown event across isolated test loops.
        sse_state = patch.object(AppStatus, 'should_exit_event', None)
        sse_state.start()
        self.addCleanup(sse_state.stop)
        self.factory = patch('foundry_agent.create_foundry_calendar_agent', new_callable=AsyncMock)
        self.create_agent = self.factory.start()
        self.addCleanup(self.factory.stop)
        self.agent = SimpleNamespace(
            create_thread=AsyncMock(
                side_effect=[SimpleNamespace(id='thread-one'), SimpleNamespace(id='thread-two')]
            ),
            run_conversation=AsyncMock(return_value=['Your calendar is available.']),
            cleanup_agent=AsyncMock(),
        )
        self.create_agent.return_value = self.agent

    async def test_executor_and_client_import_without_azure_calls(self):
        importlib.import_module('foundry_agent_executor')
        importlib.import_module('test_client')
        self.create_agent.assert_not_awaited()

    async def test_v1_parts_and_task_events(self):
        module = importlib.import_module('foundry_agent_executor')
        executor = module.FoundryAgentExecutor(AgentCard())
        queue = RecordingQueue()
        await executor.execute(
            make_context(
                parts=[
                    Part(text='Hello'),
                    Part(url='https://files.example/calendar.txt'),
                    Part(raw=b'abc'),
                    new_data_part({'ignored': True}),
                ]
            ),
            queue,
        )
        self.agent.run_conversation.assert_awaited_once_with(
            'thread-one', 'Hello [File: https://files.example/calendar.txt] [File: 3 bytes]'
        )
        self.assertEqual(queue.events[0].status.state, TaskState.TASK_STATE_SUBMITTED)
        self.assertIsInstance(queue.events[0], Task)
        self.assertEqual(queue.events[0].id, 'test-task')
        self.assertEqual(queue.events[-1].status.state, TaskState.TASK_STATE_COMPLETED)
        self.assertEqual(
            queue.events[-1].status.message.parts[0].text, 'Your calendar is available.'
        )
        for event in queue.events:
            if not isinstance(event, Task):
                self.assertEqual(event.task_id, 'test-task')
            self.assertEqual(event.context_id, 'test-context')
            if event.status.HasField('message'):
                self.assertEqual(event.status.message.task_id, 'test-task')
                self.assertEqual(event.status.message.context_id, 'test-context')

    async def test_empty_parts_keep_their_selected_content_type(self):
        module = importlib.import_module('foundry_agent_executor')
        executor = module.FoundryAgentExecutor(AgentCard())
        await executor.execute(make_context(parts=[Part(raw=b'')]), RecordingQueue())
        self.agent.run_conversation.assert_awaited_once_with('thread-one', '[File: 0 bytes]')

    async def test_missing_message_is_rejected_without_azure_calls(self):
        module = importlib.import_module('foundry_agent_executor')
        executor = module.FoundryAgentExecutor(AgentCard())
        queue = RecordingQueue()
        with self.assertRaises(InvalidParamsError):
            await executor.execute(RequestContext(call_context=ServerCallContext()), queue)
        self.assertEqual(queue.events, [])
        self.create_agent.assert_not_awaited()

    async def test_context_reuses_a_thread_without_sharing_other_contexts(self):
        module = importlib.import_module('foundry_agent_executor')
        executor = module.FoundryAgentExecutor(AgentCard())
        for task_id, context_id in [('one', 'first'), ('two', 'first'), ('three', 'second')]:
            await executor.execute(
                make_context(task_id=task_id, context_id=context_id), RecordingQueue()
            )
        self.assertEqual(self.agent.create_thread.await_count, 2)
        self.assertEqual(
            [call.args[0] for call in self.agent.run_conversation.await_args_list],
            ['thread-one', 'thread-one', 'thread-two'],
        )
        self.create_agent.assert_awaited_once()

    async def test_provider_exception_emits_failed_task(self):
        module = importlib.import_module('foundry_agent_executor')
        executor = module.FoundryAgentExecutor(AgentCard())
        self.agent.run_conversation.side_effect = RuntimeError('provider unavailable')
        queue = RecordingQueue()
        await executor.execute(make_context(), queue)
        self.assertEqual(queue.events[-1].status.state, TaskState.TASK_STATE_FAILED)
        self.assertIn('provider unavailable', queue.events[-1].status.message.parts[0].text)

    async def test_unsupported_cancellation_does_not_publish_a_false_terminal_state(self):
        module = importlib.import_module('foundry_agent_executor')
        executor = module.FoundryAgentExecutor(AgentCard())
        queue = RecordingQueue()
        with self.assertRaises(TaskNotCancelableError):
            await executor.cancel(make_context(), queue)
        self.assertEqual(queue.events, [])
        self.create_agent.assert_not_awaited()

    async def test_health_and_card_do_not_create_an_azure_agent(self):
        app = build_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=BASE_URL
        ) as http_client:
            response = await http_client.get('/health')
            self.assertEqual(response.status_code, 200)
            card = await A2ACardResolver(
                httpx_client=http_client, base_url=BASE_URL
            ).get_agent_card()
            self.assertEqual(card.name, 'AI Foundry Calendar Agent')
            self.assertEqual(card.supported_interfaces[0].protocol_binding, 'JSONRPC')
            self.assertEqual(card.supported_interfaces[0].protocol_version, '1.0')
        self.create_agent.assert_not_awaited()

    async def test_server_reports_missing_azure_configuration_before_starting(self):
        module = runpy.run_path(str(SAMPLE / '__main__.py'), run_name='foundry_test_server')
        with (
            patch.dict(os.environ, {}, clear=True),
            self.assertRaisesRegex(ValueError, 'Missing required environment variables'),
        ):
            module['main'].main(args=[], standalone_mode=False)
        self.create_agent.assert_not_awaited()

    async def test_real_sdk_client_and_routes_support_both_message_modes(self):
        app = build_app()
        for streaming in (False, True):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url=BASE_URL
            ) as http_client:
                card = await A2ACardResolver(
                    httpx_client=http_client, base_url=BASE_URL
                ).get_agent_card()
                with self.subTest(streaming=streaming):
                    client = ClientFactory(
                        ClientConfig(httpx_client=http_client, streaming=streaming)
                    ).create(card)
                    async with client:
                        events = [
                            event
                            async for event in client.send_message(
                                SendMessageRequest(
                                    message=new_text_message('Am I free?', role=Role.ROLE_USER)
                                )
                            )
                        ]
                    self.assertTrue(events)
                    terminal = events[-1]
                    task = terminal.task if terminal.HasField('task') else terminal.status_update
                    self.assertEqual(task.status.state, TaskState.TASK_STATE_COMPLETED)
                    self.assertEqual(
                        task.status.message.parts[0].text, 'Your calendar is available.'
                    )
        self.assertEqual(self.agent.run_conversation.await_count, 2)

    async def test_sample_client_runs_against_the_real_server_routes(self):
        app = build_app()
        client_module = importlib.import_module('test_client')
        async_client = httpx.AsyncClient

        def make_http_client(**kwargs):
            return async_client(transport=httpx.ASGITransport(app=app), **kwargs)

        with (
            patch.object(client_module.httpx, 'AsyncClient', side_effect=make_http_client),
            patch.dict(os.environ, {'A2A_BASE_URL': BASE_URL}),
        ):
            await client_module.main()
        self.assertEqual(self.agent.run_conversation.await_count, 10)
        self.assertEqual(self.agent.create_thread.await_count, 2)
        self.assertEqual(
            [call.args[0] for call in self.agent.run_conversation.await_args_list],
            ['thread-one'] * 5 + ['thread-two'] * 5,
        )

    async def test_sample_client_propagates_a_failed_task(self):
        app = build_app()
        client_module = importlib.import_module('test_client')
        async_client = httpx.AsyncClient
        self.agent.run_conversation.side_effect = RuntimeError('provider unavailable')

        def make_http_client(**kwargs):
            return async_client(transport=httpx.ASGITransport(app=app), **kwargs)

        with (
            patch.object(client_module.httpx, 'AsyncClient', side_effect=make_http_client),
            patch.dict(os.environ, {'A2A_BASE_URL': BASE_URL}),
            self.assertRaisesRegex(RuntimeError, 'Agent task failed'),
        ):
            await client_module.main()
        self.agent.run_conversation.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
