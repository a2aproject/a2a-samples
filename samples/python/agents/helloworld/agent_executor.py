from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types.a2a_pb2 import (
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from a2a.utils.artifact import new_text_artifact
from a2a.utils.message import new_agent_text_message
from a2a.utils.task import new_task


# --8<-- [start:HelloWorldAgent]
class HelloWorldAgent:
    """Hello World Agent."""

    async def invoke(self) -> str:
        """Invoke the Hello World agent to generate a response."""
        return 'Hello, World!'


# --8<-- [end:HelloWorldAgent]


# --8<-- [start:HelloWorldAgentExecutor_init]
class HelloWorldAgentExecutor(AgentExecutor):
    """Test AgentProxy Implementation."""

    def __init__(self) -> None:
        self.agent = HelloWorldAgent()

    # --8<-- [end:HelloWorldAgentExecutor_init]

    # --8<-- [start:HelloWorldAgentExecutor_execute]
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the agent process and enqueue the final response."""
        task = context.current_task or new_task(context.message)
        await event_queue.enqueue_event(task)

        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(
                    state=TaskState.TASK_STATE_WORKING,
                    message=new_agent_text_message('Processing request...'),
                ),
            )
        )

        result = await self.agent.invoke()

        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                artifact=new_text_artifact(name='result', text=result),
            )
        )
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(state=TaskState.TASK_STATE_COMPLETED),
            )
        )

    # --8<-- [end:HelloWorldAgentExecutor_execute]

    # --8<-- [start:HelloWorldAgentExecutor_cancel]
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Raise exception as cancel is not supported."""
        raise Exception('cancel not supported')

    # --8<-- [end:HelloWorldAgentExecutor_cancel]
