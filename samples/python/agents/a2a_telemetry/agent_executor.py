import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState, TextPart, UnsupportedOperationError
from a2a.utils import new_agent_text_message
from a2a.utils.errors import ServerError
from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search_tool
from google.genai import types


logger = logging.getLogger(__name__)


class QnAAgentExecutor(AgentExecutor):
    """Agent executor that uses the ADK to answer questions."""

    def __init__(self):
        self.agent = None
        self.runner = None

    def _init_agent(self):
        self.agent = LlmAgent(
            model='gemini-2.0-flash-exp',
            name='question_answer_agent',
            description='A helpful assistant agent that can answer questions.',
            instruction="""Respond to the query using google search""",
            tools=[google_search_tool.google_search],
        )
        self.runner = self.runner = Runner(
            app_name=self.agent.name,
            agent=self.agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise ServerError(error=UnsupportedOperationError())

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        if self.agent is None:
            self._init_agent()
        logger.debug(f'Executing agent {self.agent.name}')

        query = context.get_user_input()

        updater = TaskUpdater(event_queue, context.task_id, context.context_id)

        if not context.current_task:
            await updater.submit()

        await updater.start_work()

        content = types.Content(role='user', parts=[types.Part(text=query)])
        session = await self.runner.session_service.get_session(
            app_name=self.runner.app_name,
            user_id='123',
            session_id=context.context_id,
        ) or await self.runner.session_service.create_session(
            app_name=self.runner.app_name,
            user_id='123',
            session_id=context.context_id,
        )

        async for event in self.runner.run_async(
            session_id=session.id, user_id='123', new_message=content
        ):
            logger.debug(f'Event from ADK {event}')
            if event.is_final_response():
                parts = event.content.parts
                text_parts = [
                    TextPart(text=part.text) for part in parts if part.text
                ]
                await updater.add_artifact(
                    text_parts,
                    name='result',
                )
                await updater.complete()
                break
            await updater.update_status(
                TaskState.working, message=new_agent_text_message('Working...')
            )
        else:
            logger.debug('Agent failed to complete')
            await updater.update_status(
                TaskState.failed,
                message=new_agent_text_message(
                    'Failed to generate a response.'
                ),
            )
