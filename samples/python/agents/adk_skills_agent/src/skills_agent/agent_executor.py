import logging

from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, Task, TaskState
from a2a.utils import new_agent_text_message, new_task
from google.adk.runners import Runner
from google.genai import types

from skills_agent.agent import AgentResponse


logger = logging.getLogger(__name__)


class CurrencyAgentExecutor(AgentExecutor):
    """Executor for the Skills based Currency Agent that handles task execution."""

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
                if event.is_final_response():
                    await self._process_final_response(event, updater, task)
        except Exception:
            logger.exception('Error during agent execution')
            await self._update_task_status(
                updater,
                TaskState.TASK_STATE_FAILED,
                'An exception occurred while performing the operation',
                task,
            )

    async def _process_final_response(
        self, event: Any, updater: TaskUpdater, task: Task
    ) -> None:
        if not (
            event.content
            and event.content.parts
            and event.content.parts[0].text
        ):
            await self._update_task_status(
                updater,
                TaskState.TASK_STATE_FAILED,
                '[No text content in final event]',
                task,
            )
            return

        metadata: dict[str, Any] = {}
        final_response_text = event.content.parts[0].text.strip()

        try:
            agent_response = AgentResponse.model_validate_json(
                final_response_text
            )
            message = agent_response.message

            if agent_response.status == 'completed':
                parts = Part(text=message)
                await updater.add_artifact([parts], name='conversion_result')
                await updater.update_status(TaskState.TASK_STATE_COMPLETED)
            elif agent_response.status == 'input-required':
                await self._update_task_status(
                    updater,
                    TaskState.TASK_STATE_INPUT_REQUIRED,
                    message,
                    task,
                    metadata=metadata,
                )
            elif agent_response.status == 'failed':
                await self._update_task_status(
                    updater,
                    TaskState.TASK_STATE_FAILED,
                    message,
                    task,
                    metadata=metadata,
                )
        except Exception:
            logger.exception('Error while processing agent response')
            # Fallback to standard failure if JSON parsing fails
            await self._update_task_status(
                updater,
                TaskState.TASK_STATE_FAILED,
                final_response_text,
                task,
                metadata=metadata,
            )

    async def _update_task_status(
        self,
        updater: TaskUpdater,
        state: TaskState,
        message_text: str,
        task: Task,
        metadata: dict | None = None,
    ) -> None:
        await updater.update_status(
            state,
            new_agent_text_message(message_text, task.context_id, task.id),
            metadata=metadata,
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
