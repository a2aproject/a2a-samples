from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message


class SignedAgentExecutor(AgentExecutor):
    """Test AgentProxy Implementation."""

    def __init__(self) -> None:
        return

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the agent."""
        await event_queue.enqueue_event(new_agent_text_message("Verify me!"))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel method is not supported."""

        raise Exception("Cancel not supported.")
