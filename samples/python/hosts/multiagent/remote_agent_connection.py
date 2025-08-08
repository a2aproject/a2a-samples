import traceback

from collections.abc import Callable

from a2a.client import (
    Client,
    ClientFactory,
)
from a2a.types import (
    AgentCard,
    Message,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
)


TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]


class RemoteAgentConnections:
    """A class to hold the connections to the remote agents."""

    def __init__(self, client_factory: ClientFactory, agent_card: AgentCard):
        self.agent_client: Client = client_factory.create(agent_card)
        self.card: AgentCard = agent_card
        self.pending_tasks = set()

    def get_agent(self) -> AgentCard:
        return self.card

    async def send_message(self, message: Message) -> Task | Message | None:
        lastTask: Task | None = None
        try:
            async for event in self.agent_client.send_message(message):
                if isinstance(event, Message):
                    return event
                if self.is_terminal_or_interrupted(event[0]):
                    return event[0]
                lastTask = event[0]
        except Exception as e:
            print('Exception found in send_message')
            traceback.print_exc()
            raise e
        return lastTask

    def is_terminal_or_interrupted(self, task: Task) -> bool:
        return task.status.state in [
            TaskState.completed,
            TaskState.canceled,
            TaskState.failed,
            TaskState.input_required,
            TaskState.unknown,
        ]
