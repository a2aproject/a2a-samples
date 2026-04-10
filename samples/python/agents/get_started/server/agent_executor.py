# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    Part,
    Task,
    TaskState,
    UnsupportedOperationError,
)
from a2a.utils import (
    new_agent_text_message,
    new_task,
)

# Loading from agent.py
from agent import WeatherReportingPoet


class WeatherReportingPoetExecutor(AgentExecutor):
    """Poet's interface to A2A Clients."""

    def __init__(self) -> None:
        self.agent = WeatherReportingPoet()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        To execute the agent's logic for a given request context.
        """
        # Collect users request
        query = context.get_user_input()

        ## Task
        # Look for current task (Tasks mentioned here is an A2A data construct)
        # If this request does not have current task, create a new one and use it.
        task = None
        if not context.current_task:
            task = new_task(context.message)  # Create task
            await event_queue.enqueue_event(task)  # Add task to A2A's Event Queue
        else:
            task = context.current_task  # Refer to existing queue

        ## Event Queue
        # Acts as a buffer the agent's asynchronous execution and the server's response handling
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        # invoke the underlying agent, using streaming results. The streams
        # now are update events.
        async for finished, text in self.agent.stream(query, task.context_id):
            if not finished:
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(text, task.context_id, task.id),
                )
                continue
            # Emit the appropriate events
            await updater.add_artifact(
                [Part(text=text)],
                name="response",
            )
            await updater.complete()
            break

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise UnsupportedOperationError("Error: Streaming Operation not supported")
