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


class SignedAgentExecutor(AgentExecutor):
    """Test AgentProxy Implementation."""

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the agent and manage task lifecycle events."""
        if context.current_task:
            task = context.current_task
        else:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        task_updater = TaskUpdater(
            event_queue=event_queue, task_id=task.id, context_id=task.context_id
        )
        await task_updater.update_status(
            state=TaskState.TASK_STATE_WORKING,
            message=new_text_message('Processing verification request...'),
        )

        query = get_message_text(context.message)
        if query:
            result = f'Verify me! ({query})'
        else:
            result = 'Verify me!'

        await task_updater.add_artifact(parts=[new_text_part(text=result, media_type='text/plain')])

        await task_updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message('Request is completed!'),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Raise exception as cancel is not supported."""
        raise NotImplementedError('Cancel is not supported.')
