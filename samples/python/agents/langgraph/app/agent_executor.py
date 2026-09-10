import logging

from typing import override

from a2a.helpers import (
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.utils.errors import (
    InternalError,
    InvalidParamsError,
    UnsupportedOperationError,
)

from app.agent import CurrencyAgent


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CurrencyAgentExecutor(AgentExecutor):
    """Currency Conversion AgentExecutor Example."""

    def __init__(self) -> None:
        self.agent = CurrencyAgent()

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        error = self._validate_request(context)
        if error:
            raise InvalidParamsError

        query = context.get_user_input()
        task = context.current_task
        if not task:
            if not context.message:
                raise InvalidParamsError('Message is required')
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)
        try:
            async for item in self.agent.stream(query, task.context_id):
                is_task_complete = item['is_task_complete']
                require_user_input = item['require_user_input']

                if not is_task_complete and not require_user_input:
                    msg = new_text_message(
                        text=item['content'],
                        task_id=task.id,
                        context_id=task.context_id,
                    )
                    await updater.start_work(message=msg)
                elif require_user_input:
                    msg = new_text_message(
                        text=item['content'],
                        task_id=task.id,
                        context_id=task.context_id,
                    )
                    await updater.requires_input(message=msg)
                    break
                else:
                    await updater.add_artifact(
                        parts=[new_text_part(item['content'])],
                        name='conversion_result',
                    )
                    await updater.complete()
                    break

        except Exception as e:
            logger.exception('An error occurred while streaming the response')
            raise InternalError from e

    def _validate_request(self, context: RequestContext) -> bool:
        return False

    @override
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise UnsupportedOperationError
