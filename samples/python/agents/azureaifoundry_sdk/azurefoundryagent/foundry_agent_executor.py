"""AI Foundry Agent Executor for A2A framework.

Adapted from ADK agent executor pattern to work with Azure AI Foundry agents.
"""

import logging

from collections.abc import Iterable

import foundry_agent

from a2a.helpers import new_task_from_user_message
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCard,
    Part,
    TaskState,
)
from a2a.utils.errors import InvalidParamsError, TaskNotCancelableError


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class FoundryAgentExecutor(AgentExecutor):
    """An AgentExecutor that runs Azure AI Foundry-based agents.

    Adapted from the ADK agent executor pattern.
    """

    def __init__(self, card: AgentCard):
        self._card = card
        self._foundry_agent: foundry_agent.FoundryCalendarAgent | None = None
        self._active_threads: dict[str, str] = {}  # context_id -> thread_id mapping

    async def _get_or_create_agent(self) -> foundry_agent.FoundryCalendarAgent:
        """Get or create the Foundry calendar agent."""
        if not self._foundry_agent:
            self._foundry_agent = await foundry_agent.create_foundry_calendar_agent()
        return self._foundry_agent

    async def _get_or_create_thread(self, context_id: str) -> str:
        """Get or create a thread for the given context."""
        if context_id not in self._active_threads:
            agent = await self._get_or_create_agent()
            thread = await agent.create_thread()
            self._active_threads[context_id] = thread.id
            logger.info('Created new thread %s for context %s', thread.id, context_id)

        return self._active_threads[context_id]

    async def _process_request(
        self,
        message_parts: Iterable[Part],
        context_id: str,
        task_updater: TaskUpdater,
    ) -> None:
        """Process a user request through the Foundry agent."""
        try:
            # Convert A2A parts to text message
            user_message = self._convert_parts_to_text(message_parts)

            # Get agent and thread
            agent = await self._get_or_create_agent()
            thread_id = await self._get_or_create_thread(context_id)

            # Update status
            await task_updater.update_status(
                TaskState.TASK_STATE_WORKING,
                message=task_updater.new_agent_message([Part(text='Processing your request...')]),
            )

            # Run the conversation
            responses = await agent.run_conversation(thread_id, user_message)

            # Send responses back
            for response in responses:
                await task_updater.update_status(
                    TaskState.TASK_STATE_WORKING,
                    message=task_updater.new_agent_message([Part(text=response)]),
                )

            # Mark as complete
            final_message = responses[-1] if responses else 'Task completed.'
            await task_updater.complete(
                message=task_updater.new_agent_message([Part(text=final_message)])
            )

        except Exception as e:
            logger.exception('Error processing request')
            await task_updater.failed(
                message=task_updater.new_agent_message([Part(text=f'Error: {e!s}')])
            )

    def _convert_parts_to_text(self, parts: Iterable[Part]) -> str:
        """Convert A2A message parts to a text string."""
        text_parts = []

        for part in parts:
            content_type = part.WhichOneof('content')
            if content_type == 'text':
                text_parts.append(part.text)
            elif content_type == 'url':
                text_parts.append(f'[File: {part.url}]')
            elif content_type == 'raw':
                text_parts.append(f'[File: {len(part.raw)} bytes]')
            else:
                logger.warning('Unsupported part content: %s', content_type)

        return ' '.join(text_parts)

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the agent request."""
        logger.info('Executing request for context: %s', context.context_id)

        message = context.message
        if message is None:
            raise InvalidParamsError(message='A message is required.')
        task = context.current_task
        if task is None:
            task = new_task_from_user_message(message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        # Start working
        await updater.start_work()

        # Process the request
        await self._process_request(
            message.parts,
            task.context_id,
            updater,
        )

        logger.debug('Foundry agent execution completed for %s', context.context_id)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Reject cancellation because the sample does not stop Foundry runs."""
        raise TaskNotCancelableError(
            message='This sample does not support cancelling Foundry runs.'
        )

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._foundry_agent:
            await self._foundry_agent.cleanup_agent()
            self._foundry_agent = None
        self._active_threads.clear()
        logger.info('Foundry agent executor cleaned up')


def create_foundry_agent_executor(card: AgentCard) -> FoundryAgentExecutor:
    """Factory function to create a Foundry agent executor."""
    return FoundryAgentExecutor(card)
