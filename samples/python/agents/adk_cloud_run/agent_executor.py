from typing import Any

from a2a.helpers import (
    get_message_text,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


class ADKAgentExecutor(AgentExecutor):
    """A2A AgentExecutor backed by a Google ADK Runner."""

    def __init__(
        self,
        agent: Any,
        status_message: str = 'Processing request...',
        artifact_name: str = 'response',
    ) -> None:
        """Initialize a generic ADK agent executor.

        Args:
            agent: The ADK agent instance
            status_message: Message to display while processing
            artifact_name: Name for the response artifact
        """
        self.agent = agent
        self.status_message = status_message
        self.artifact_name = artifact_name
        self.runner = Runner(
            app_name=agent.name,
            agent=agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Cancel the execution of a specific task."""
        raise NotImplementedError('Cancellation is not implemented for ADKAgentExecutor.')

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute an incoming A2A task using the ADK runner."""
        if not context.message:
            raise ValueError('Message should be present in request context')

        query = get_message_text(context.message)
        if context.current_task:
            task = context.current_task
        else:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)
        if context.call_context and context.call_context.user.is_authenticated:
            user_id = context.call_context.user.user_name
        else:
            user_id = 'a2a_user'

        try:
            # Update status with custom message
            await updater.update_status(
                TaskState.TASK_STATE_WORKING,
                new_text_message(
                    self.status_message,
                    context_id=task.context_id,
                    task_id=task.id,
                ),
            )

            # Process with ADK agent
            session = await self.runner.session_service.get_session(
                app_name=self.agent.name,
                user_id=user_id,
                session_id=task.context_id,
            )
            if session is None:
                session = await self.runner.session_service.create_session(
                    app_name=self.agent.name,
                    user_id=user_id,
                    state={},
                    session_id=task.context_id,
                )

            content = types.Content(role='user', parts=[types.Part.from_text(text=query)])

            response_text = ''
            async for event in self.runner.run_async(
                user_id=user_id, session_id=session.id, new_message=content
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text + '\n'
                        elif hasattr(part, 'function_call'):
                            # Log or handle function calls if needed
                            pass  # Function calls are handled internally by ADK

            # Add response as artifact with custom name
            await updater.add_artifact(
                [new_text_part(text=response_text.strip(), media_type='text/plain')],
                name=self.artifact_name,
            )

            await updater.update_status(TaskState.TASK_STATE_COMPLETED)

        except Exception as e:  # noqa: BLE001
            await updater.update_status(
                TaskState.TASK_STATE_FAILED,
                new_text_message(
                    f'Error: {e!s}',
                    context_id=task.context_id,
                    task_id=task.id,
                ),
            )
