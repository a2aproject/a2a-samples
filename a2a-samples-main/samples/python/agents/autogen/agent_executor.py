from typing_extensions import override
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message
from .agent import CurrencyAgent

class CurrencyAgentExecutor(AgentExecutor):
    """Executor that adapts CurrencyAgent to A2A SDK interface."""

    def __init__(self):
        self.agent = CurrencyAgent()

    @override
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        parts = context.call_context.message.parts
        user_input = ''
        for part in parts:
            if getattr(part, 'type', None) == 'text' or getattr(part, 'kind', None) == 'text':
                user_input = part.text
                break
        response = self.agent.invoke(user_input, context.call_context.context_id)
        event_queue.enqueue_event(new_agent_text_message(response['content']))

    @override
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError('Cancellation is not supported.')
