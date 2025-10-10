from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import TaskState, TextPart, UnsupportedOperationError, Message
from a2a.utils.errors import ServerError
from a2a.types import TaskArtifactUpdateEvent, TaskStatusUpdateEvent, TaskStatus, TaskState, TextPart, UnsupportedOperationError, Message
from a2a.utils import new_agent_text_message, new_task, new_text_artifact

from agent.agent import HostAgent
from a2a.types import AgentCard
import logging
import traceback
import json
from pprint import pformat

logger = logging.getLogger("host_agent.agent_executor")

class HostAgentExecutor(AgentExecutor):

    def __init__(self, agent_cards:list[AgentCard]):
        self.agent = HostAgent(agent_cards)
        self.agent_cards = agent_cards
    
    async def execute(
        self, 
        context:RequestContext, 
        event_queue:EventQueue
    ) -> None:
        metadata = context._params.message.metadata
        session_id = metadata.get("session_id", None)
        user_id = metadata.get("user_id", None)
        query = context.get_user_input()
        task = context.current_task

        try :

            if not task :
                task = new_task(context.message)
                await event_queue.enqueue_event(new_task(context.message))
            
            async for event in self.agent.invoke(query, session_id, task.id, user_id):
                if isinstance(event, TaskArtifactUpdateEvent):
                    event_dict = event.dict()
                    text=""
                    for part in event_dict["artifact"]["parts"]:
                        text = part['text']

                    await event_queue.enqueue_event(
                                TaskArtifactUpdateEvent(
                                    taskId=task.id,
                                    contextId=task.contextId,
                                    artifact=new_text_artifact(
                                        name='host_agent_result',
                                        description='호스트 에이전트 결과',
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
                elif isinstance(event, TaskStatusUpdateEvent):
                    text=""
                    if(event.final == False):
                        event_dict = event.dict()
                        text = event_dict['status']['message']['parts'][0]['text']
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
        except Exception as e :
            traceback.print_exc()
            raise ServerError(f"Error executing host agent: {e}")

    
    async def cancel(self, context: RequestContext, event_queue: EventQueue):
            raise ServerError(error=UnsupportedOperationError())        

            


            
