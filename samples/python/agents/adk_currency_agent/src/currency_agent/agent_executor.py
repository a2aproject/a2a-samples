import logging
import os

from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, TaskState, TextPart
from a2a.utils import new_agent_text_message, new_task
from google.adk.runners import Runner
from google.genai import types

from currency_agent.agent import AgentResponse
from currency_agent.traceability import (
    TRACEABILITY_EXTENSION_URI,
    CallTypeEnum,
    ResponseTrace,
    TraceStep,
)


logger = logging.getLogger(__name__)

TRACE_KEY = (
    'github.com/a2aproject/a2a-samples/extensions/traceability/v1/traceability'
)


class CurrencyAgentExecutor(AgentExecutor):
    """Executor for the Currency Agent that handles task execution and traceability."""

    def __init__(self, runner: Runner):
        self._runner = runner

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Executes the agent task based on the provided context."""
        context_id = context.context_id

        query = context.get_user_input()
        content = types.Content(
            role='user', parts=[types.Part.from_text(text=query)]
        )

        response_trace = None
        logger.info('Requested extensions: %s', context.requested_extensions)
        if TRACEABILITY_EXTENSION_URI in context.requested_extensions:
            # Only enable traceability in non-production environments
            if os.getenv('ENV', 'production') != 'production':
                context.add_activated_extension(TRACEABILITY_EXTENSION_URI)
                response_trace = ResponseTrace()
                logger.info('Traceability Extension Activated')
            else:
                logger.warning(
                    'Traceability Extension requested but disabled in production'
                )

        await self.ensure_session(context_id)  # type: ignore

        task = context.current_task
        if not task:
            task = new_task(context.message)  # type: ignore
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        try:
            async for event in self._runner.run_async(
                user_id=context_id, session_id=context_id, new_message=content
            ):  # type: ignore
                if response_trace:
                    self._process_trace_events(event, response_trace)

                if event.is_final_response():
                    await self._process_final_response(
                        event, updater, response_trace, task
                    )

        except Exception:
            logger.exception('Error during agent execution')
            await self._update_task_status(
                updater,
                TaskState.failed,
                'An exception occurred while performing the operation',
                task,
            )

    def _process_trace_events(
        self, event: Any, response_trace: ResponseTrace
    ) -> None:
        function_calls = event.get_function_calls()
        if function_calls:
            for function_call in function_calls:
                if function_call.name == 'set_model_response':
                    continue
                with TraceStep(
                    response_trace,
                    CallTypeEnum.TOOL,
                    name=function_call.name,
                    parameters=function_call.args,
                    step_type='tool_call',
                ) as tool_call_step:
                    tool_call_step.end_step()

        function_responses = event.get_function_responses()
        if function_responses:
            for function_response in function_responses:
                if function_response.name == 'set_model_response':
                    continue
                with TraceStep(
                    response_trace,
                    CallTypeEnum.TOOL,
                    name=function_response.name,
                    parameters={'response': function_response.response},
                    step_type='tool_response',
                ) as tool_response_step:
                    tool_response_step.end_step()

    async def _process_final_response(
        self,
        event: Any,
        updater: TaskUpdater,
        response_trace: ResponseTrace | None,
        task: Any,
    ) -> None:
        if not (
            event.content
            and event.content.parts
            and event.content.parts[0].text
        ):
            await self._update_task_status(
                updater,
                TaskState.failed,
                '[No text content in final event]',
                task,
            )
            return

        metadata = (
            {TRACE_KEY: response_trace.as_dict()} if response_trace else {}
        )
        final_response_text = event.content.parts[0].text.strip()

        try:
            agent_response = AgentResponse.model_validate_json(
                final_response_text
            )
            message = agent_response.message

            if agent_response.status == 'completed':
                parts = [Part(root=TextPart(text=message))]
                await updater.add_artifact(parts, name='conversion_result')
                await self._update_task_status(
                    updater,
                    TaskState.completed,
                    message,
                    task,
                    metadata=metadata,
                    final=True,
                )
            elif agent_response.status == 'input-required':
                await self._update_task_status(
                    updater,
                    TaskState.input_required,
                    message,
                    task,
                    metadata=metadata,
                    final=True,
                )
            elif agent_response.status == 'failed':
                await self._update_task_status(
                    updater,
                    TaskState.failed,
                    message,
                    task,
                    metadata=metadata,
                    final=True,
                )
        except Exception:  # noqa: BLE001
            # Fallback to standard failure if JSON parsing fails
            await self._update_task_status(
                updater,
                TaskState.failed,
                final_response_text,
                task,
                metadata=metadata,
                final=True,
            )

    async def _update_task_status(  # noqa: PLR0913
        self,
        updater: TaskUpdater,
        state: TaskState,
        message_text: str,
        task: Any,
        metadata: dict | None = None,
        final: bool = False,
    ) -> None:
        await updater.update_status(
            state,
            new_agent_text_message(message_text, task.context_id, task.id),
            metadata=metadata,
            final=final,
        )

    async def ensure_session(self, context_id: str) -> None:
        """Ensures that a session exists for the given context ID."""
        session = await self._runner.session_service.get_session(
            app_name=self._runner.app_name,
            user_id=context_id,
            session_id=context_id,
        )
        if session is None:
            await self._runner.session_service.create_session(
                app_name=self._runner.app_name,
                user_id=context_id,
                session_id=context_id,
            )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Cancel the agent execution.

        Args:
            context: The request context.
            event_queue: The event queue.

        """
        raise NotImplementedError('Cancellation is not supported')
