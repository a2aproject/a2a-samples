from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types import TaskArtifactUpdateEvent, TaskStatusUpdateEvent, TaskStatus, TaskState
from a2a.utils import new_agent_text_message, new_task, new_text_artifact
from a2a.utils.errors import ServerError
from a2a.types import TaskState, TextPart, UnsupportedOperationError, Message

from agent.agent import SearchAgent
from a2a.types import AgentCard
import logging
logger = logging.getLogger("search_agent.agent_executor")

class SearchAgentExecutor(AgentExecutor):
    def __init__(self):
        self.agent = SearchAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        metadata = context._params.message.metadata
        session_id = metadata.get("session_id", None)
        user_id = metadata.get("user_id", None)
        query = context.get_user_input()
        task = context.current_task
        try:
            if not task :
                task = new_task(context.message)
                await event_queue.enqueue_event(task)
            logger.info(f"invoke 진입전 ")
            async for event in self.agent.invoke(query, session_id, task.id, user_id):
                event_dict = event.dict()
                text = event_dict['content']['parts'][0]['text']
                is_final = event.is_final_response()
                if is_final:
                    logger.info(f"event: {event}")
                    await event_queue.enqueue_event(
                        TaskArtifactUpdateEvent(
                            taskId=task.id,
                            contextId=task.contextId,
                            artifact=new_text_artifact(
                                name='search_result',
                                description='검색 결과',
                                text=text,
                            ),
                            append=False,
                            lastChunk=True,
                        )
                    )
                    await event_queue.enqueue_event(
                        TaskStatusUpdateEvent(
                            taskId=task.id,
                            contextId=task.contextId,
                            status=TaskStatus(state=TaskState.completed),
                            final=True
                        )
                    )
                else :
                    await event_queue.enqueue_event(
                        TaskStatusUpdateEvent(
                            taskId=task.id,
                            contextId=task.contextId,
                            status=TaskStatus(
                                state=TaskState.working,
                                message=new_agent_text_message(
                                    text,
                                    task.id,
                                    task.contextId,
                                ),
                            ),
                            final=False,
                        )
                    )
        except Exception as e:
            logger.error(f"[EXECUTE] 예외 발생: {e}", exc_info=True)
            raise

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        """Cancels an ongoing operation."""
        raise ServerError(error=UnsupportedOperationError())      

