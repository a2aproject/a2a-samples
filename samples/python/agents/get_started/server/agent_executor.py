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

from a2a import types
from a2a.helpers import new_task_from_user_message, new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue

# Loading from agent.py
from agent import WeatherReportingPoet


class WeatherReportingPoetExecutor(AgentExecutor):
    """Poet's interface to A2A Clients."""

    def __init__(self) -> None:
        # task queue
        self.running_tasks: set[str] = set()
        # AI Agent
        self.agent = WeatherReportingPoet()

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """To execute the agent's logic for a given request context.
        """
        # Collect users request
        query = context.get_user_input()

        ## Task
        # Look for current task (Tasks mentioned here is an A2A data construct)
        # If this request does not have current task, create a new one and use it.
        task = None
        if not context.current_task:
            task = new_task_from_user_message(context.message)  # Create task
            await event_queue.enqueue_event(
                task
            )  # Add task to A2A's Event Queue
        else:
            task = context.current_task  # Refer to existing queue

        ## Event Queue
        # Acts as a buffer the agent's asynchronous execution and the server's response handling
        # updater = TaskUpdater(event_queue, task.id, task.context_id)
        # 3. Update task status as working
        _task_update = types.a2a_pb2.TaskStatusUpdateEvent(
            task_id=task.id,
            context_id=context.context_id,
            status=types.TaskStatus(
                state=types.TaskState.TASK_STATE_WORKING,
                message=new_text_message('START'),
            ),
        )
        await event_queue.enqueue_event(_task_update)

        # invoke the agent
        print(f'User> {query}')
        async for finished, text in self.agent.stream(query, task.id):
            if not finished:
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
        raise Exception('cancel not supported')
