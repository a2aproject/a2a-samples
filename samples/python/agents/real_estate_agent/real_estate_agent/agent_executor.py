import json
import logging
from a2a.server.agent_execution import AgentExecutor
from a2a.server.events import EventQueue
from a2a.types import MessageSendParams
from a2a.utils import new_agent_text_message
from .mcp_clients.dafty_mcp_client import DaftyMcpClient
from mcp.types import TextContent

class RealEstateAgentExecutor(AgentExecutor):
    """Real Estate Agent Executor."""

    def __init__(self):
        self.mcp_client = DaftyMcpClient()

    async def execute(
        self,
        request: MessageSendParams,
        event_queue: EventQueue,
    ) -> None:
        try:
            async with self.mcp_client as client:
                if not request.message.parts:
                    await event_queue.enqueue_event(new_agent_text_message("Invalid request: message is empty."))
                    return

                # The content is nested in the 'root' attribute of the first part.
                content = request.message.parts[0].root
                
                # Check if the content has a 'text' attribute to robustly get the query.
                if hasattr(content, 'text'):
                    query = content.text
                else:
                    logging.error(f"Unexpected message content structure: {content}")
                    await event_queue.enqueue_event(new_agent_text_message("Invalid request: message content is not recognized."))
                    return
                
                # Call the new parse_query tool
                parsed_params_parts = await client.call_tool("parse_query", {"query": query})
                if not parsed_params_parts or not isinstance(parsed_params_parts[0], TextContent):
                    await event_queue.enqueue_event(new_agent_text_message("Could not understand your request."))
                    return
                
                try:
                    filters = json.loads(parsed_params_parts[0].text)
                except json.JSONDecodeError:
                    await event_queue.enqueue_event(new_agent_text_message("Error: Could not parse the query parameters."))
                    return

                result_parts = await client.search_rental_properties(filters)

                if not result_parts or not isinstance(result_parts[0], TextContent):
                    await event_queue.enqueue_event(new_agent_text_message("No results found."))
                    return

                # The actual data is a JSON string inside the first text part
                try:
                    properties = json.loads(result_parts[0].text)
                except json.JSONDecodeError:
                    await event_queue.enqueue_event(new_agent_text_message("Error: Could not parse the property results."))
                    return
                
                if not properties:
                    await event_queue.enqueue_event(new_agent_text_message("No properties matched your criteria."))
                    return

                # Process and format the result before sending
                formatted_result = json.dumps(properties, indent=2)
                
                await event_queue.enqueue_event(new_agent_text_message(formatted_result))
        except RuntimeError as e:
            # Propagate specific tool errors from the MCP client
            await event_queue.enqueue_event(new_agent_text_message(f"An error occurred: {e}"))
        except Exception:
            # In a production system, you would log the full error `e`
            # For other unexpected errors, provide a generic message
            logging.exception("An unexpected error occurred in RealEstateAgentExecutor")
            await event_queue.enqueue_event(new_agent_text_message("An unexpected error occurred while processing your request."))

    async def cancel(
        self, request: MessageSendParams, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')