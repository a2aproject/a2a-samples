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


class EchoAgent:
    """Echo Agent."""

    async def invoke(self, user_request: str) -> str:
        """Invoke the Echo agent to generate a response."""
        return f'hello! ({user_request})' if user_request else 'hello!'


class EchoExecutor(AgentExecutor):
    """Echo Executor implementation."""

    def __init__(self) -> None:
        self.agent = EchoAgent()

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
            message=new_text_message('working...'),
        )

        query = get_message_text(context.message)
        result = await self.agent.invoke(user_request=query)

        await task_updater.add_artifact(parts=[new_text_part(text=result, media_type='text/plain')])

        await task_updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message('Request is completed!'),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel the execution of the task."""
        raise NotImplementedError('Cancel is not supported.')
