"""Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import traceback

from collections.abc import Callable

from a2a.client import Client, ClientFactory
from a2a.types import (
    AgentCard,
    Message,
    SendMessageRequest,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
)
from dotenv import load_dotenv


load_dotenv()

TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]


class RemoteAgentConnections:
    """A class to hold the connections to the remote agents."""

    def __init__(self, client_factory: ClientFactory, agent_card: AgentCard):
        self.agent_client: Client = client_factory.create(agent_card)
        self.card = agent_card

    def get_agent(self) -> AgentCard:
        return self.card

    async def send_message(self, request: SendMessageRequest) -> Task | Message | None:
        last_task: Task | None = None
        try:
            async for stream_response in self.agent_client.send_message(request):
                if stream_response.HasField('message'):
                    return stream_response.message
                if stream_response.HasField('task'):
                    task = stream_response.task
                    if self.is_terminal_or_interrupted(task):
                        return task
                    last_task = task
        except Exception as e:
            print('Exception found in send_message')
            traceback.print_exc()
            raise e
        return last_task

    def is_terminal_or_interrupted(self, task: Task) -> bool:
        return task.status.state in [
            TaskState.TASK_STATE_COMPLETED,
            TaskState.TASK_STATE_CANCELED,
            TaskState.TASK_STATE_FAILED,
            TaskState.TASK_STATE_INPUT_REQUIRED,
        ]
