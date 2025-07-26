from typing import override

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from a2a.utils import new_text_artifact
from agent import TravelPlannerAgent


class TravelPlannerAgentExecutor(AgentExecutor):
    """travel planner AgentExecutor Example."""

    def __init__(self):
        self.agent = TravelPlannerAgent()

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        query = context.get_user_input()
        if not context.message:
            raise Exception('No message provided')

        async for event in self.agent.stream(query):
            message = TaskArtifactUpdateEvent(
                contextId=context.context_id, # type: ignore
                taskId=context.task_id, # type: ignore
                artifact=new_text_artifact(
                    name='current_result',
                    text=event['content'],
                ),
            )
            await event_queue.enqueue_event(message)
            if event['done']:
                break

        status = TaskStatusUpdateEvent(
            contextId=context.context_id, # type: ignore
            taskId=context.task_id, # type: ignore
            status=TaskStatus(state=TaskState.completed),
            final=True
        )
        await event_queue.enqueue_event(status)

    @override
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')
