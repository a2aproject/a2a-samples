import uuid

from typing import override

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    Artifact,
    Part,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from a2a.utils import new_agent_text_message, new_task

from no_llm_framework.server.agent import Agent


class HelloWorldAgentExecutor(AgentExecutor):
    """Test AgentProxy Implementation."""

    def __init__(self) -> None:
        self.agent = Agent(
            mode='stream',
            token_stream_callback=print,
            mcp_url='https://gitmcp.io/google/A2A',
        )

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        query = context.get_user_input()
        task = context.current_task

        if not context.message:
            raise Exception('No message provided')

        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        artifact_id = str(uuid.uuid4())
        first_chunk = True

        async for event in self.agent.stream(query):
            if event['is_task_complete']:
                await event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        append=not first_chunk,
                        context_id=task.context_id,
                        task_id=task.id,
                        last_chunk=True,
                        artifact=Artifact(
                            artifact_id=artifact_id,
                            name='current_result',
                            description='Result of request to agent.',
                            parts=[Part(text=event['content'])],
                        ),
                    )
                )
                await event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        status=TaskStatus(state=TaskState.TASK_STATE_COMPLETED),
                        context_id=task.context_id,
                        task_id=task.id,
                    )
                )
            elif event['require_user_input']:
                await event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        status=TaskStatus(
                            state=TaskState.TASK_STATE_INPUT_REQUIRED,
                            message=new_agent_text_message(
                                event['content'],
                                task.context_id,
                                task.id,
                            ),
                        ),
                        context_id=task.context_id,
                        task_id=task.id,
                    )
                )
                first_chunk = False
            else:
                if first_chunk:
                    await event_queue.enqueue_event(
                        TaskStatusUpdateEvent(
                            status=TaskStatus(
                                state=TaskState.TASK_STATE_WORKING,
                            ),
                            context_id=task.context_id,
                            task_id=task.id,
                        )
                    )
                await event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        append=not first_chunk,
                        context_id=task.context_id,
                        task_id=task.id,
                        last_chunk=False,
                        artifact=Artifact(
                            artifact_id=artifact_id,
                            name='current_result',
                            description='Result of request to agent.',
                            parts=[Part(text=event['content'])],
                        ),
                    )
                )
                first_chunk = False

    @override
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')
