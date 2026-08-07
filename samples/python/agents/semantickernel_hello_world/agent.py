import asyncio
import logging
import os

from collections.abc import AsyncIterable
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any, Literal

from dotenv import load_dotenv
from pydantic import BaseModel
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    OpenAIChatCompletion,
    OpenAIChatPromptExecutionSettings,
)
from semantic_kernel.contents import (
    FunctionCallContent,
    FunctionResultContent,
    StreamingChatMessageContent,
    StreamingTextContent,
)
from semantic_kernel.functions import KernelArguments, kernel_function


if TYPE_CHECKING:
    from semantic_kernel.connectors.ai.chat_completion_client_base import (
        ChatCompletionClientBase,
    )
    from semantic_kernel.contents import ChatMessageContent

logger = logging.getLogger(__name__)

load_dotenv()

# region Chat Service Configuration


class ChatServices(str, Enum):
    """Enum for supported chat completion services."""

    AZURE_OPENAI = 'azure_openai'
    OPENAI = 'openai'


service_id = 'default'


def get_chat_completion_service(
    service_name: ChatServices,
) -> 'ChatCompletionClientBase':
    """Return an appropriate chat completion service based on the service name.

    Args:
        service_name (ChatServices): Service name.

    Returns:
        ChatCompletionClientBase: Configured chat completion service.

    Raises:
        ValueError: If the service name is not supported or required environment variables are missing.
    """
    if service_name == ChatServices.AZURE_OPENAI:
        return _get_azure_openai_chat_completion_service()
    if service_name == ChatServices.OPENAI:
        return _get_openai_chat_completion_service()
    raise ValueError(f'Unsupported service name: {service_name}')


def _get_azure_openai_chat_completion_service() -> AzureChatCompletion:
    """Return Azure OpenAI chat completion service.

    Returns:
        AzureChatCompletion: The configured Azure OpenAI service.
    """
    return AzureChatCompletion(service_id=service_id)


def _get_openai_chat_completion_service() -> OpenAIChatCompletion:
    """Return OpenAI chat completion service.

    Returns:
        OpenAIChatCompletion: Configured OpenAI service.
    """
    return OpenAIChatCompletion(
        service_id=service_id,
        ai_model_id=os.getenv('OPENAI_MODEL_ID'),
        api_key=os.getenv('OPENAI_API_KEY'),
    )


# endregion

# region Calculator Plugin

import ast
import math

_ALLOWED_NAMES = {k: getattr(math, k) for k in [
    'pi', 'e', 'tau', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'sqrt', 'log', 'log10', 'floor', 'ceil'
]}
_ALLOWED_NAMES.update({'abs': abs, 'round': round, 'min': min, 'max': max})
_ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Num,  # py<3.8
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
    ast.FloorDiv,
    ast.USub,
    ast.UAdd,
    ast.Call,
    ast.Load,
    ast.Name,
)


def _safe_eval(expr: str) -> float:
    """Safely evaluate a mathematical expression using a restricted AST."""
    try:
        tree = ast.parse(expr, mode='eval')
        for node in ast.walk(tree):
            if not isinstance(node, _ALLOWED_NODES):
                raise ValueError(f'Unsupported expression element: {type(node).__name__}')
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_NAMES:
                    raise ValueError('Only whitelisted math functions are allowed')
        compiled = compile(tree, '<expr>', 'eval')
        return float(eval(compiled, {'__builtins__': {}}, _ALLOWED_NAMES))  # noqa: S307 (controlled env)
    except Exception as e:  # noqa: BLE001
        raise ValueError(f'Invalid expression: {e!s}') from e


class CalculatorPlugin:
    """A calculator plugin providing arithmetic operations and expression evaluation."""

    @kernel_function(description='Add two numbers')
    def add(
        self,
        a: Annotated[float, 'First number'],
        b: Annotated[float, 'Second number'],
    ) -> str:
        return str(a + b)

    @kernel_function(description='Subtract two numbers (a - b)')
    def subtract(
        self,
        a: Annotated[float, 'Minuend'],
        b: Annotated[float, 'Subtrahend'],
    ) -> str:
        return str(a - b)

    @kernel_function(description='Multiply two numbers')
    def multiply(
        self,
        a: Annotated[float, 'First factor'],
        b: Annotated[float, 'Second factor'],
    ) -> str:
        return str(a * b)

    @kernel_function(description='Divide two numbers (a / b)')
    def divide(
        self,
        a: Annotated[float, 'Dividend'],
        b: Annotated[float, 'Divisor (non-zero)'],
    ) -> str:
        try:
            return str(a / b)
        except ZeroDivisionError:
            return 'Error: Division by zero'

    @kernel_function(description='Evaluate a math expression safely (supports +, -, *, /, **, sin, cos, etc.)')
    def calculate(
        self,
        expression: Annotated[str, 'Mathematical expression to evaluate'],
    ) -> str:
        try:
            return str(_safe_eval(expression))
        except Exception as e:  # noqa: BLE001
            return f'Error: {e!s}'


# endregion

# region Response Format


class ResponseFormat(BaseModel):
    """A Response Format model to direct how the model should respond."""

    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str


# endregion

# region Semantic Kernel Calculator Agent


class SemanticKernelCalculatorAgent:
    """Calculator agent powered by Semantic Kernel with tool/function calling."""

    agent: ChatCompletionAgent
    thread: ChatHistoryAgentThread = None
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self):
        # Choose backend (Azure OpenAI by default)
        chat_service = get_chat_completion_service(ChatServices.AZURE_OPENAI)

        calculator_agent = ChatCompletionAgent(
            service=chat_service,
            name='CalculatorToolAgent',
            instructions=(
                'You are a precise mathematical tool. Use the provided calculator functions to compute results. '
                'Always prefer tool calls over doing math in your head for reliability. '
                'Support arithmetic, safe expression evaluation, and basic math functions. '
                'If the user asks something non-mathematical, politely explain you are a calculator.'
            ),
            plugins=[CalculatorPlugin()],
        )

        self.agent = ChatCompletionAgent(
            service=chat_service,
            name='CalculatorManagerAgent',
            instructions=(
                'You manage mathematical queries. Decide if a direct answer is possible or if a tool should be called. '
                'Use the CalculatorToolAgent for any computation beyond trivial arithmetic. '
                'Return concise answers. For step-by-step requests, explain steps briefly.'
            ),
            plugins=[calculator_agent],
            arguments=KernelArguments(
                settings=OpenAIChatPromptExecutionSettings(
                    response_format=ResponseFormat,
                )
            ),
        )

    async def invoke(self, user_input: str, session_id: str) -> dict[str, Any]:
        """Handle synchronous tasks (like message/send).

        Args:
            user_input (str): User input message.
            session_id (str): Unique identifier for the session.

        Returns:
            dict: A dictionary containing the content, task completion status,
            and user input requirement.
        """
        await self._ensure_thread_exists(session_id)

        # Use SK's get_response for a single shot
        response = await self.agent.get_response(
            messages=user_input,
            thread=self.thread,
        )
        return self._get_agent_response(response.content)

    async def stream(
        self,
        user_input: str,
        session_id: str,
    ) -> AsyncIterable[dict[str, Any]]:
        """For streaming tasks we yield the SK agent's invoke_stream progress.

        Args:
            user_input (str): User input message.
            session_id (str): Unique identifier for the session.

        Yields:
            dict: A dictionary containing the content, task completion status,
            and user input requirement.
        """
        await self._ensure_thread_exists(session_id)

        plugin_notice_seen = False
        plugin_event = asyncio.Event()

        text_notice_seen = False
        chunks: list[StreamingChatMessageContent] = []

        async def _handle_intermediate_message(
            message: 'ChatMessageContent',
        ) -> None:
            """Handle intermediate messages from the agent."""
            nonlocal plugin_notice_seen
            if not plugin_notice_seen:
                plugin_notice_seen = True
                plugin_event.set()
            # An example of handling intermediate messages during function calling
            for item in message.items or []:
                if isinstance(item, FunctionResultContent):
                    logger.info(
                        'Tool Result: %s for function: %s', item.result, item.name
                    )
                elif isinstance(item, FunctionCallContent):
                    logger.info(
                        'Tool Call: %s with arguments: %s', item.name, item.arguments
                    )
                else:
                    logger.debug('Intermediate message item: %s', item)

        async for chunk in self.agent.invoke_stream(
            messages=user_input,
            thread=self.thread,
            on_intermediate_message=_handle_intermediate_message,
        ):
            if plugin_event.is_set():
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Computing with calculator tools...',
                }
                plugin_event.clear()

            if any(isinstance(i, StreamingTextContent) for i in chunk.items):
                if not text_notice_seen:
                    yield {
                        'is_task_complete': False,
                        'require_user_input': False,
                        'content': 'Formulating result...',
                    }
                    text_notice_seen = True
                chunks.append(chunk.message)

        if chunks:
            yield self._get_agent_response(sum(chunks[1:], chunks[0]))

    def _get_agent_response(
        self, message: 'ChatMessageContent'
    ) -> dict[str, Any]:
        try:
            structured_response = ResponseFormat.model_validate_json(
                message.content
            )
        except Exception:  # noqa: BLE001
            # Fallback: return raw content
            return {
                'is_task_complete': True,
                'require_user_input': False,
                'content': message.content,
            }

        default_response = {
            'is_task_complete': True,
            'require_user_input': False,
            'content': 'Unable to process the request.',
        }

        if isinstance(structured_response, ResponseFormat):
            response_map = {
                'input_required': {
                    'is_task_complete': False,
                    'require_user_input': True,
                },
                'error': {
                    'is_task_complete': True,
                    'require_user_input': False,
                },
                'completed': {
                    'is_task_complete': True,
                    'require_user_input': False,
                },
            }
            response = response_map.get(structured_response.status)
            if response:
                return {**response, 'content': structured_response.message}
        return default_response

    async def _ensure_thread_exists(self, session_id: str) -> None:
        """Ensure the thread exists for the given session ID.

        Args:
            session_id (str): Unique identifier for the session.
        """
        if self.thread is None or self.thread.id != session_id:
            await self.thread.delete() if self.thread else None
            self.thread = ChatHistoryAgentThread(thread_id=session_id)


# endregion
