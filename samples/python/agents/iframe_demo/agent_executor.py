"""Agent executor for the iframe demo agent."""

import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message

from agent import IframeDemoAgent


logger = logging.getLogger(__name__)


class IframeDemoAgentExecutor(AgentExecutor):
    """Executor for the iframe demo agent."""

    def __init__(self):
        """Initialize the executor."""
        self.agent = IframeDemoAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the agent task."""
        try:
            # Extract text from the request message
            message_text = self._extract_text_from_context(context)
            
            logger.info(f"Processing message: {message_text}")
            
            # Generate response using the agent
            response_parts = await self.agent.generate_response(message_text)
            
            # Send each part as a separate message
            for part in response_parts:
                message = new_agent_text_message(
                    context.task.id,
                    context.message.context_id,
                    ""  # Will be replaced with the actual part content
                )
                # Replace the text part with our iframe part
                message.parts = [part]
                await event_queue.send_message(message)

        except Exception as e:
            logger.exception(f"Error executing task: {e}")
            
            # Send error message
            error_message = new_agent_text_message(
                context.task.id,
                context.message.context_id,
                f"Error processing request: {str(e)}"
            )
            await event_queue.send_message(error_message)

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Cancel the agent execution (required abstract method)."""
        logger.info("Canceling iframe demo agent execution")
        # Nothing specific to cancel for this demo agent

    def _extract_text_from_context(self, context: RequestContext) -> str:
        """Extract text content from request context."""
        message = context.message
        text_parts = []
        
        for part in message.parts:
            if part.root.kind == 'text':
                text_parts.append(part.root.text)
            elif part.root.kind == 'data':
                # Try to extract text from data parts if possible
                try:
                    if isinstance(part.root.data, dict) and 'text' in part.root.data:
                        text_parts.append(part.root.data['text'])
                    elif isinstance(part.root.data, str):
                        text_parts.append(part.root.data)
                except Exception:
                    # Skip non-text data parts
                    pass
                    
        return ' '.join(text_parts) if text_parts else "Hello"