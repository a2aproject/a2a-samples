import json
import logging

from typing import Any

from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCard,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError
from anthropic import AsyncAnthropic


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class AnthropicAgentExecutor(AgentExecutor):
    """An AgentExecutor that runs an Anthropic Claude-based Agent."""

    def __init__(
        self,
        card: AgentCard,
        tools: dict[str, Any],
        api_key: str,
        system_prompt: str,
    ):
        self._card = card
        self.tools = tools
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = 'claude-sonnet-4-20250514'
        self.system_prompt = system_prompt

    async def _process_request(
        self,
        message_text: str,
        context: RequestContext,
        task_updater: TaskUpdater,
    ) -> None:
        messages = [
            {'role': 'user', 'content': message_text},
        ]

        # Convert tools to Anthropic format
        anthropic_tools = []
        for tool_name, tool_instance in self.tools.items():
            if hasattr(tool_instance, tool_name):
                func = getattr(tool_instance, tool_name)
                # Extract function schema from the method
                schema = self._extract_function_schema(func)
                anthropic_tools.append(schema)

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            try:
                # Make API call to Anthropic
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    system=self.system_prompt,
                    messages=messages,
                    tools=anthropic_tools if anthropic_tools else None,
                )

                # Process response content blocks
                assistant_content = []
                tool_use_blocks = []
                text_content = ""

                for block in response.content:
                    if block.type == 'text':
                        text_content += block.text
                        assistant_content.append({'type': 'text', 'text': block.text})
                    elif block.type == 'tool_use':
                        tool_use_blocks.append(block)
                        assistant_content.append({
                            'type': 'tool_use',
                            'id': block.id,
                            'name': block.name,
                            'input': block.input
                        })

                # Add assistant's response to messages
                messages.append({
                    'role': 'assistant',
                    'content': assistant_content
                })

                # Check if there are tool calls to execute
                if tool_use_blocks:
                    tool_results = []

                    for tool_use in tool_use_blocks:
                        function_name = tool_use.name
                        function_args = tool_use.input

                        logger.debug(
                            f'Calling function: {function_name} with args: {function_args}'
                        )

                        # Execute the function
                        if function_name in self.tools:
                            tool_instance = self.tools[function_name]
                            # Get the method from the instance
                            if hasattr(tool_instance, function_name):
                                method = getattr(tool_instance, function_name)
                                result = method(**function_args)
                            else:
                                result = {
                                    'error': f'Method {function_name} not found on tool instance'
                                }
                        else:
                            result = {
                                'error': f'Function {function_name} not found'
                            }

                        # Serialize result properly - handle Pydantic models
                        if hasattr(result, 'model_dump'):
                            result_json = json.dumps(result.model_dump())
                        elif isinstance(result, dict):
                            result_json = json.dumps(result)
                        else:
                            result_json = str(result)

                        tool_results.append({
                            'type': 'tool_result',
                            'tool_use_id': tool_use.id,
                            'content': result_json
                        })

                    # Add tool results to messages
                    messages.append({
                        'role': 'user',
                        'content': tool_results
                    })

                    # Send update to show we're processing
                    await task_updater.update_status(
                        TaskState.working,
                        message=task_updater.new_agent_message(
                            [TextPart(text='Processing tool calls...')]
                        ),
                    )

                    # Continue the loop to get the final response
                    continue

                # No more tool calls, check stop reason
                if response.stop_reason == 'end_turn' or text_content:
                    if text_content:
                        parts = [TextPart(text=text_content)]
                        logger.debug(f'Yielding final response: {parts}')
                        await task_updater.add_artifact(parts)
                    await task_updater.complete()
                break

            except Exception as e:
                logger.error(f'Error in Anthropic API call: {e}')
                error_parts = [
                    TextPart(
                        text=f'Sorry, an error occurred while processing the request: {e!s}'
                    )
                ]
                await task_updater.add_artifact(error_parts)
                await task_updater.complete()
                break

        if iteration >= max_iterations:
            error_parts = [
                TextPart(
                    text='Sorry, the request has exceeded the maximum number of iterations.'
                )
            ]
            await task_updater.add_artifact(error_parts)
            await task_updater.complete()

    def _extract_function_schema(self, func):
        """Extract Anthropic tool schema from a Python function"""
        import inspect

        # Get function signature
        sig = inspect.signature(func)

        # Get docstring
        docstring = inspect.getdoc(func) or ''

        # Extract description and parameter info from docstring
        lines = docstring.split('\n')
        description = lines[0] if lines else func.__name__

        # Build parameters schema
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            param_type = 'string'  # Default type
            param_description = f'Parameter {param_name}'

            # Try to infer type from annotation
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = 'integer'
                elif param.annotation == float:
                    param_type = 'number'
                elif param.annotation == bool:
                    param_type = 'boolean'
                elif param.annotation == list:
                    param_type = 'array'
                elif param.annotation == dict:
                    param_type = 'object'

            # Check if parameter has default value
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

            properties[param_name] = {
                'type': param_type,
                'description': param_description,
            }

        return {
            'name': func.__name__,
            'description': description,
            'input_schema': {
                'type': 'object',
                'properties': properties,
                'required': required,
            },
        }

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ):
        # Run the agent until complete
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        # Immediately notify that the task is submitted.
        if not context.current_task:
            await updater.submit()
        await updater.start_work()

        # Extract text from message parts
        message_text = ''
        for part in context.message.parts:
            if isinstance(part.root, TextPart):
                message_text += part.root.text

        await self._process_request(message_text, context, updater)
        logger.debug('[GitHub Agent] execute exiting')

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        # Ideally: kill any ongoing tasks.
        raise ServerError(error=UnsupportedOperationError())
