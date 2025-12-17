from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message


# --8<-- [start:SignedAgent]
class SignedAgent:
    """Signed Agent."""

    async def invoke(self) -> str:
        return 'Verify me!'


# --8<-- [end:SignedAgent]


# --8<-- [start:SignedAgentExecutor_init]
class SignedAgentExecutor(AgentExecutor):
    """Test AgentProxy Implementation."""

    def __init__(self) -> None:
        self.agent = SignedAgent()

    # --8<-- [end:SignedAgentExecutor_init]
    # --8<-- [start:SignedAgentExecutor_execute]
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        result = await self.agent.invoke()
        await event_queue.enqueue_event(new_agent_text_message(result))

    # --8<-- [end:SignedAgentExecutor_execute]

    # --8<-- [start:SignedAgentExecutor_cancel]
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')

    # --8<-- [end:SignedAgentExecutor_cancel]
