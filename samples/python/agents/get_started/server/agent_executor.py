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

"""Module defining the A2A AgentExecutor for the Weather Reporting Poet."""

from a2a import types
from a2a.helpers import new_task_from_user_message, new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue

# Import the core agent logic
from agent import WeatherReportingPoet


class WeatherReportingPoetExecutor(AgentExecutor):
    """Poet's interface to A2A Clients.

    This class handles incoming A2A requests, manages task state,
    and interacts with the underlying WeatherReportingPoet agent.
    """

    def __init__(self) -> None:
        """Initializes the executor with a task tracker and the core agent."""
        # Track currently running tasks
        self.running_tasks: set[str] = set()
        # The core AI Agent instance
        self.agent = WeatherReportingPoet()

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Executes the agent's logic for a given A2A request context.

        Args:
            context: The request context containing user message and task info.
            event_queue: The queue to send A2A events back to the client.
        """
        # Extract the user's query from the context
        query = context.get_user_input()

        # Manage the A2A Task construct
        task = None
        if not context.current_task:
            # Create a new task if none exists for this request
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)
        else:
            # Refer to the existing task
            task = context.current_task

        # Send a TaskStatusUpdateEvent indicating the agent has started working
        _task_update = types.a2a_pb2.TaskStatusUpdateEvent(
            task_id=task.id,
            context_id=context.context_id,
            status=types.TaskStatus(
                state=types.TaskState.TASK_STATE_WORKING,
                message=new_text_message('START'),
            ),
        )
        await event_queue.enqueue_event(_task_update)

        print(f'User> {query}')

        # Stream the response from the core agent and forward to event queue
        async for finished, text in self.agent.stream(query, task.id):
            if not finished:
                # Send intermediate status updates
                _task_update = types.a2a_pb2.TaskStatusUpdateEvent(
                    task_id=task.id,
                    context_id=context.context_id,
                    status=types.TaskStatus(
                        state=types.TaskState.TASK_STATE_WORKING,
                        message=new_text_message(f'User: {query}'),
                    ),
                )
                await event_queue.enqueue_event(_task_update)
            else:
                # Send final completed status with the full generated text
                _task_update = types.a2a_pb2.TaskStatusUpdateEvent(
                    task_id=task.id,
                    context_id=context.context_id,
                    status=types.TaskStatus(
                        state=types.TaskState.TASK_STATE_COMPLETED,
                        message=new_text_message(f'Response: {text}'),
                    ),
                )
                await event_queue.enqueue_event(_task_update)
                print(f'Model> {text}')
                break

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Cancels the execution of a running task."""
        raise Exception('cancel not supported')

