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
from agent import DiceAgent


class DiceAgentExecutor(AgentExecutor):
    """Reimbursement AgentExecutor Example."""

    def __init__(self) -> None:
        self.agent = DiceAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Run the dice agent for a request and publish task updates."""
        query = get_message_text(context.message)
        task = context.current_task

        # This agent always produces Task objects. If this request does
        # not have current task, create a new one and use it.
        if not task:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        # invoke the underlying agent, using streaming results. The streams
        # now are update events.
        async for finished, text in self.agent.stream(query, task.context_id):
            if not finished:
                await updater.update_status(
                    TaskState.TASK_STATE_WORKING,
                    new_text_message(text, context_id=task.context_id, task_id=task.id),
                )
                continue
            # Emit the appropriate events
            await updater.add_artifact(
                [new_text_part(text, media_type='text/plain')],
                name='response',
            )
            await updater.complete()
            break

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Raise exception as cancel is not supported."""
        raise NotImplementedError('Cancel is not supported.')
