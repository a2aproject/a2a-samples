from a2a.helpers import new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Role


class SignedAgentExecutor(AgentExecutor):
    """Test AgentProxy Implementation."""

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the agent."""
        await event_queue.enqueue_event(new_text_message('Verify me!', role=Role.ROLE_AGENT))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Raise exception as cancel is not supported."""
        raise NotImplementedError('Cancel is not supported.')
