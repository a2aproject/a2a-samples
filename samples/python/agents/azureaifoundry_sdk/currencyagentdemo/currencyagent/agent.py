import json
import logging
import os
import time

from collections.abc import AsyncGenerator
from typing import Any

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    Agent,
    AgentThread,
    ListSortOrder,
    ThreadMessage,
    ThreadRun,
    ToolOutput,
)
from azure.identity import DefaultAzureCredential
from utils.mcp_tool_manager import MCPToolManager


class CurrencyAgent:
    logger = logging.getLogger(__name__)

    INSTRUCTION = (
        'You are a specialized assistant for currency conversions. '
        "Your sole purpose is to use the 'get_exchange_rate' tool to answer questions about currency exchange rates. "
        'If the user asks about anything other than currency conversion or exchange rates, '
        'politely state that you cannot help with that topic and can only assist with currency-related queries. '
        'Do not attempt to answer unrelated questions or use tools for other purposes.'
        'Set response status to input_required if the user needs to provide more information.'
        'Set response status to error if there is an error while processing the request.'
        'Set response status to completed if the request is complete.'
    )

    def __init__(self):
        # Check if required environment variable exists
        if 'AZURE_AI_FOUNDRY_PROJECT_ENDPOINT' not in os.environ:
            raise ValueError(
                'AZURE_AI_FOUNDRY_PROJECT_ENDPOINT environment variable is not set. '
                'Please configure your Azure AI Foundry endpoint.'
            )

        self.endpoint = os.environ['AZURE_AI_FOUNDRY_PROJECT_ENDPOINT']

        # Check if endpoint value is valid
        if not self.endpoint or not self.endpoint.strip():
            raise ValueError(
                'AZURE_AI_FOUNDRY_PROJECT_ENDPOINT environment variable is empty. '
                'Please provide a valid Azure AI Foundry endpoint.'
            )

        self.credential = DefaultAzureCredential()
        self.agent: Agent | None = None
        self.threads: dict[str, str] = {}  # thread_id -> thread_id mapping
        self.mcp_server_url = os.environ.get('MCP_ENDPOINT')
        self.mcp_tool_manager: MCPToolManager | None = (
            None  # Placeholder for MCPToolManager or similar
        )

    def _get_client(self) -> AgentsClient:
        """Get a new AgentsClient instance for use in context managers."""
        return AgentsClient(
            endpoint=self.endpoint,
            credential=self.credential,
        )

    async def create_agent(self) -> Agent:
        """Create the AI Foundry agent with calendar instructions."""
        if self.agent:
            return self.agent

        logger = logging.getLogger(__name__)

        self.mcp_tool_manager = MCPToolManager(self.mcp_server_url)

        # Initialize the MCP tool manager (without async context manager)
        await self.mcp_tool_manager.initialize()

        # Get all available tool definitions
        mcp_tools = self.mcp_tool_manager.get_tools()

        if not mcp_tools:
            raise ValueError(
                'No valid MCP tools found. Please check your MCP server configuration.'
            )

        logger.info(
            f'Found {len(mcp_tools)} MCP tools: {list(mcp_tools.keys())}'
        )

        # Convert MCP tools to Azure AI Agents format
        azure_tools = []
        for tool_name, tool_def in mcp_tools.items():
            logger.info(f'Processing tool: {tool_name}')
            logger.info(f'Tool definition: {tool_def}')

            azure_tool_def = {
                'type': 'function',
                'function': {
                    'name': tool_def['name'],
                    'description': tool_def['description'],
                    'parameters': tool_def['input_schema'],
                },
            }
            azure_tools.append(azure_tool_def)
            logger.info(f'Converted to Azure tool: {azure_tool_def}')

        with self._get_client() as client:
            self.agent = client.create_agent(
                model=os.environ['AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME'],
                name='currency-agent',
                instructions=self.INSTRUCTION,
                tools=azure_tools,
            )
            return self.agent

    async def create_thread(self, thread_id: str | None = None) -> AgentThread:
        """Create or retrieve a conversation thread."""
        if thread_id and thread_id in self.threads:
            # Return thread info - we'll need to get it fresh each time
            pass

        with self._get_client() as client:
            thread = client.threads.create()
            self.threads[thread.id] = thread.id
            return thread

    async def send_message(
        self, thread_id: str, content: str, role: str = 'user'
    ) -> ThreadMessage:
        """Send a message to the conversation thread."""
        with self._get_client() as client:
            message = client.messages.create(
                thread_id=thread_id, role=role, content=content
            )
            return message

    async def run_conversation(
        self, thread_id: str, user_message: str
    ) -> list[str]:
        """Run a complete conversation cycle with the agent."""
        if not self.agent:
            await self.create_agent()

        # Send user message
        await self.send_message(thread_id, user_message)

        # Create and run the agent
        with self._get_client() as client:
            run = client.runs.create(
                thread_id=thread_id, agent_id=self.agent.id
            )

            # Poll until completion
            max_iterations = 30  # Prevent infinite loops
            iterations = 0

            while (
                run.status in ['queued', 'in_progress', 'requires_action']
                and iterations < max_iterations
            ):
                iterations += 1
                time.sleep(1)
                run = client.runs.get(thread_id=thread_id, run_id=run.id)

                if run.status == 'failed':
                    break

                # Handle tool calls if needed
                if run.status == 'requires_action':
                    try:
                        await self._handle_tool_calls(run, thread_id)
                        # Get updated run status after tool submission
                        run = client.runs.get(
                            thread_id=thread_id, run_id=run.id
                        )
                    except Exception as e:
                        # logger.error(f"Error handling tool calls: {e}")
                        # If tool handling fails, mark the run as failed
                        return [f'Error handling tool calls: {e!s}']

            if run.status == 'failed':
                # logger.error(f"Run failed: {run.last_error}")
                return [f'Error: {run.last_error}']

            if iterations >= max_iterations:
                # logger.error(f"Run timed out after {max_iterations} iterations")
                return ['Error: Request timed out']

            # Get response messages
            messages = client.messages.list(
                thread_id=thread_id, order=ListSortOrder.DESCENDING
            )

            responses = []
            for msg in messages:
                if msg.role == 'assistant' and msg.text_messages:
                    for text_msg in msg.text_messages:
                        responses.append(text_msg.text.value)
                    break  # Only get the latest assistant response

            return responses if responses else ['No response received']

    async def stream(
        self, user_query: str, context_id: str = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream responses from the agent.

        Args:
            user_query: The user's query text
            context_id: Optional context ID for conversation tracking

        Yields:
            Dictionary with streaming response information
        """
        # Create thread if needed or reuse existing thread
        if not context_id or context_id not in self.threads:
            thread = await self.create_thread()
            thread_id = thread.id
            if context_id:
                self.threads[context_id] = thread_id
        else:
            thread_id = self.threads[context_id]

        # Make sure the agent exists
        if not self.agent:
            await self.create_agent()

        # Send user message
        await self.send_message(thread_id, user_query)

        # Initial response for working state
        yield {
            'content': 'Working on your request...',
            'require_user_input': False,
            'is_task_complete': False,
        }

        # Create and run the agent
        with self._get_client() as client:
            run = client.runs.create(
                thread_id=thread_id, agent_id=self.agent.id
            )

            max_iterations = 30
            iterations = 0

            while (
                run.status in ['queued', 'in_progress', 'requires_action']
                and iterations < max_iterations
            ):
                iterations += 1
                time.sleep(0.5)  # Shorter polling interval for streaming

                run = client.runs.get(thread_id=thread_id, run_id=run.id)

                # If we need tool calls, handle them
                if run.status == 'requires_action':
                    try:
                        yield {
                            'content': 'Processing data sources...',
                            'require_user_input': False,
                            'is_task_complete': False,
                        }
                        await self._handle_tool_calls(run, thread_id)
                        run = client.runs.get(
                            thread_id=thread_id, run_id=run.id
                        )
                    except Exception as e:
                        yield {
                            'content': f'Error handling tool calls: {e!s}',
                            'require_user_input': False,
                            'is_task_complete': True,
                        }
                        return

            # Handle any terminal states
            if run.status == 'failed':
                yield {
                    'content': f'Error: {run.last_error}',
                    'require_user_input': False,
                    'is_task_complete': True,
                }
                return

            if iterations >= max_iterations:
                yield {
                    'content': 'Error: Request timed out',
                    'require_user_input': False,
                    'is_task_complete': True,
                }
                return

            # Get final response
            messages = client.messages.list(
                thread_id=thread_id, order=ListSortOrder.DESCENDING
            )

            for msg in messages:
                if msg.role == 'assistant' and msg.text_messages:
                    for text_msg in msg.text_messages:
                        yield {
                            'content': text_msg.text.value,
                            'require_user_input': False,
                            'is_task_complete': True,
                        }
                    return

            # Fallback if no message found
            yield {
                'content': 'No response received from the agent.',
                'require_user_input': False,
                'is_task_complete': True,
            }

    async def _handle_tool_calls(self, run: ThreadRun, thread_id: str):
        """Handle tool calls during agent execution using MCP tool manager."""
        import logging

        logger = logging.getLogger(__name__)
        logger.info('Handling MCP tool calls')

        if not hasattr(run, 'required_action') or not run.required_action:
            logger.warning('No required action found in run')
            return

        required_action = run.required_action
        if (
            not hasattr(required_action, 'submit_tool_outputs')
            or not required_action.submit_tool_outputs
        ):
            logger.warning('No tool outputs required')
            return

        try:
            tool_calls = required_action.submit_tool_outputs.tool_calls
            if not tool_calls:
                logger.warning('No tool calls found in required action')
                return

            tool_outputs = []

            # Ensure MCP Tool Manager is initialized and connected
            if not self.mcp_tool_manager:
                logger.warning('MCP Tool Manager not initialized, creating now')
                self.mcp_tool_manager = MCPToolManager(self.mcp_server_url)
                await self.mcp_tool_manager.initialize()
            elif (
                not self.mcp_tool_manager._connection
                or not self.mcp_tool_manager._connection.is_connected
            ):
                logger.warning(
                    'MCP Tool Manager connection not available, reinitializing'
                )
                await self.mcp_tool_manager.initialize()

            # Process each tool call
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                arguments_str = tool_call.function.arguments

                logger.info(
                    f'Processing mcp tool call: {function_name} with args: {arguments_str}'
                )

                try:
                    # Parse arguments from JSON string with defensive handling
                    if not arguments_str or arguments_str.strip() == '':
                        logger.warning(
                            f'Empty or null arguments for tool {function_name}, using empty dict'
                        )
                        arguments = {}
                    else:
                        try:
                            arguments = json.loads(arguments_str)
                            logger.info(f'Parsed arguments: {arguments}')
                            logger.info(f'Arguments type: {type(arguments)}')
                            logger.info(
                                f'Arguments keys: {list(arguments.keys()) if isinstance(arguments, dict) else "Not a dict"}'
                            )
                        except json.JSONDecodeError as json_error:
                            logger.error(
                                f'Failed to parse JSON arguments for tool {function_name}: {json_error}'
                            )
                            logger.error(
                                f"Raw arguments string: '{arguments_str}'"
                            )
                            # Try to recover by using empty arguments or skip this tool call
                            arguments = {}
                            logger.warning(
                                f'Using empty arguments for tool {function_name} due to JSON parse error'
                            )

                    # Check if the function exists in MCP tools
                    available_tools = self.mcp_tool_manager.get_tools()
                    if function_name in available_tools:
                        logger.info(
                            f'Executing MCP tool function: {function_name} with arguments: {arguments}'
                        )

                        # Debug: Log the exact argument values
                        if isinstance(arguments, dict):
                            for key, value in arguments.items():
                                logger.info(
                                    f"  Argument '{key}': '{value}' (type: {type(value)})"
                                )

                        # Ensure connection exists before using it
                        if not self.mcp_tool_manager._connection:
                            logger.error(
                                'MCP connection is None after initialization'
                            )
                            output = {'error': 'MCP connection not available'}
                        else:
                            # Execute the MCP tool directly using the connection
                            output = await self.mcp_tool_manager._connection.execute_tool(
                                function_name, arguments
                            )
                            logger.info(f'MCP tool execution result: {output}')
                    else:
                        output = {'error': f'Unknown function: {function_name}'}
                        logger.error(
                            f'Unknown function requested: {function_name}'
                        )
                        logger.error(
                            f'Available tools: {list(available_tools.keys())}'
                        )

                except json.JSONDecodeError as e:
                    output = {'error': f'Invalid arguments JSON: {e!s}'}
                    logger.error(
                        f'JSON parsing error for tool {function_name}: {e!s}'
                    )
                except Exception as e:
                    output = {
                        'error': f'Error executing tool {function_name}: {e!s}'
                    }
                    logger.error(f'Error during tool execution: {e!s}')
                    logger.error(f'Exception type: {type(e).__name__}')
                    import traceback

                    logger.error(f'Full traceback: {traceback.format_exc()}')

                # Ensure we have a valid tool_call_id
                if not hasattr(tool_call, 'id') or not tool_call.id:
                    logger.error(f'Tool call missing ID: {tool_call}')
                    continue

                # Convert output to JSON string if it's not already
                if isinstance(output, str):
                    output_str = output
                else:
                    output_str = json.dumps(output)

                tool_outputs.append(
                    {'tool_call_id': tool_call.id, 'output': output_str}
                )

            if not tool_outputs:
                logger.error('No valid tool outputs generated')
                return

            logger.debug(f'Tool outputs to submit: {tool_outputs}')

        except Exception as e:
            logger.error(f'Error processing tool calls: {e}')
            logger.error(f'Required action structure: {required_action}')
            raise

        # Submit the tool outputs
        with self._get_client() as client:
            try:
                # Create tool outputs in the expected format
                formatted_outputs = []
                for output in tool_outputs:
                    formatted_outputs.append(
                        ToolOutput(
                            tool_call_id=output['tool_call_id'],
                            output=output['output'],
                        )
                    )

                logger.debug(
                    f'Submitting formatted tool outputs: {formatted_outputs}'
                )

                client.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=formatted_outputs,
                )
                logger.info(f'Submitted {len(formatted_outputs)} tool outputs')
            except Exception as e:
                logger.error(f'Failed to submit tool outputs: {e}')
                logger.error(f'Raw tool outputs structure: {tool_outputs}')
                # Try submitting without ToolOutput wrapper as fallback
                try:
                    logger.info(
                        'Trying fallback submission with raw dict format'
                    )
                    client.runs.submit_tool_outputs(
                        thread_id=thread_id,
                        run_id=run.id,
                        tool_outputs=tool_outputs,
                    )
                    logger.info('Fallback submission successful')
                except Exception as e2:
                    logger.error(f'Fallback submission also failed: {e2}')
                    raise e

    async def cleanup_agent(self):
        """Clean up the agent resources."""
        if self.agent:
            with self._get_client() as client:
                client.delete_agent(self.agent.id)
                # logger.info(f"Deleted agent: {self.agent.id}")
                self.agent = None

        # Clean up MCP connection
        if self.mcp_tool_manager:
            await self.mcp_tool_manager.close()
            self.mcp_tool_manager = None


async def create_foundry_calendar_agent() -> CurrencyAgent:
    """Factory function to create and initialize a Foundry calendar agent."""
    agent = CurrencyAgent()
    await agent.create_agent()
    return agent
