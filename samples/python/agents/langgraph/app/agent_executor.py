import logging

from a2a.helpers import (
    new_task_from_user_message,
    new_text_artifact_update_event,
    new_text_status_update_event,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    InternalError,
    InvalidParamsError,
    TaskState,
    UnsupportedOperationError,
)

from app.agent import CurrencyAgent


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CurrencyAgentExecutor(AgentExecutor):
    """Currency Conversion AgentExecutor Example."""

    def __init__(self):
        self.agent = CurrencyAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        error = self._validate_request(context)
        if error:
            raise InvalidParamsError

        query = context.get_user_input()
        task = context.current_task or new_task_from_user_message(context.message)
        await event_queue.enqueue_event(task)
        try:
            async for item in self.agent.stream(query, task.context_id):
                is_task_complete = item['is_task_complete']
                require_user_input = item['require_user_input']

                if not is_task_complete and not require_user_input:
                    await event_queue.enqueue_event(
                        new_text_status_update_event(
                            task_id=task.id,
                            context_id=task.context_id,
                            state=TaskState.TASK_STATE_WORKING,
                            text=item['content'],
                        )
                    )
                elif require_user_input:
                    await event_queue.enqueue_event(
                        new_text_status_update_event(
                            task_id=task.id,
                            context_id=task.context_id,
                            state=TaskState.TASK_STATE_INPUT_REQUIRED,
                            text=item['content'],
                        )
                    )
                    break
                else:
                    await event_queue.enqueue_event(
                        new_text_artifact_update_event(
                            task_id=task.id,
                            context_id=task.context_id,
                            name='conversion_result',
                            text=item['content'],
                        )
                    )
                    await event_queue.enqueue_event(
                        new_text_status_update_event(
                            task_id=task.id,
                            context_id=task.context_id,
                            state=TaskState.TASK_STATE_COMPLETED,
                            text='',
                        )
                    )
                    break

        except Exception as e:
            logger.error(f'An error occurred while streaming the response: {e}')
            raise InternalError from e

    def _validate_request(self, context: RequestContext) -> bool:
        return False

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise UnsupportedOperationError
