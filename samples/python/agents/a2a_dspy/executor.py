from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Task,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import (
    new_agent_text_message,
)
from a2a.utils.errors import ServerError
from braintrust import current_span, traced

from agents.dspy_example import agent
from logger import logger
from memory.mem0 import Mem0Memory


class DspyAgentExecutor(AgentExecutor):
    """Memory-aware DSPy AgentExecutor with per-user context."""

    def __init__(self) -> None:
        self.agent = agent
        self.memory = Mem0Memory()

    @traced
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the task."""
        with logger.start_span():
            error = self._validate_request(context)
            if error:
                raise ServerError(error=InvalidParamsError())

            updater = TaskUpdater(
                event_queue, context.task_id, context.context_id
            )
            if not context.current_task:
                await updater.submit()

            await updater.start_work()

            query = context.get_user_input()
            try:
                ctx = await self.memory.retrieve(
                    query=query, user_id=context.context_id
                )
                result = self.agent(question=str(query), ctx=ctx)
                current_span().log(input=query, output=result.answer)
                await self.memory.save(
                    user_id=context.context_id,
                    user_input=query,
                    assistant_response=result.answer,
                )
            except Exception as e:
                current_span().log(error=e)
                raise ServerError(error=InternalError()) from e
            if result.completed_task:
                await updater.add_artifact(
                    [TextPart(text=result.answer)],
                    name='answer',
                )
                await updater.complete()
            else:
                await updater.update_status(
                    TaskState.input_required,
                    message=new_agent_text_message(
                        result.answer, context.context_id, context.task_id
                    ),
                )

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        """Cancel the task."""
        raise ServerError(error=UnsupportedOperationError())

    def _validate_request(self, context: RequestContext) -> bool:
        return False
