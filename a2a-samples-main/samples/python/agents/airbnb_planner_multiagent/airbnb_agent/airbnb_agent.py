# ruff: noqa: E501
# pylint: disable=logging-fstring-interpolation
import logging
import os

from collections.abc import AsyncIterable
from typing import Any, Literal

import httpx

from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.runnables.config import (
    RunnableConfig,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import ChatVertexAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel


logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO)

memory = MemorySaver()


class ResponseFormat(BaseModel):
    """Respond to the user in this format."""

    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str


class AirbnbAgent:
    """Airbnb Agent Example."""

    SYSTEM_INSTRUCTION = """You are a specialized assistant for Airbnb accommodations. Your primary function is to utilize the provided tools to search for Airbnb listings and answer related questions. You must rely exclusively on these tools for information; do not invent listings or prices. Ensure that your Markdown-formatted response includes all relevant tool output, with particular emphasis on providing direct links to listings"""

    RESPONSE_FORMAT_INSTRUCTION: str = (
        'Select status as "completed" if the request is fully addressed and no further input is needed. '
        'Select status as "input_required" if you need more information from the user or are asking a clarifying question. '
        'Select status as "error" if an error occurred or the request cannot be fulfilled.'
    )

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self, mcp_tools: list[Any]):  # Modified to accept mcp_tools
        """Initializes the Airbnb agent.

        Args:
            mcp_tools: A list of preloaded MCP (Model Context Protocol) tools.
        """
        logger.info('Initializing AirbnbAgent with preloaded MCP tools...')
        try:
            model = os.getenv('GOOGLE_GENAI_MODEL')
            if not model:
                raise ValueError(
                    'GOOGLE_GENAI_MODEL environment variable is not set'
                )

            if os.getenv('GOOGLE_GENAI_USE_VERTEXAI') == 'TRUE':
                # If not using Vertex AI, initialize with Google Generative AI
                logger.info('ChatVertexAI model initialized successfully.')
                self.model = ChatVertexAI(model=model)

            else:
                # Using the model name from your provided file
                self.model = ChatGoogleGenerativeAI(model=model)
                logger.info(
                    'ChatGoogleGenerativeAI model initialized successfully.'
                )

        except Exception as e:
            logger.error(
                f'Failed to initialize ChatGoogleGenerativeAI model: {e}',
                exc_info=True,
            )
            raise

        self.mcp_tools = mcp_tools
        if not self.mcp_tools:
            raise ValueError('No MCP tools provided to AirbnbAgent')

    async def ainvoke(self, query: str, session_id: str) -> dict[str, Any]:
        logger.info(
            f"Airbnb.ainvoke called with query: '{query}', session_id: '{session_id}'"
        )
        try:
            airbnb_agent_runnable = create_react_agent(
                self.model,
                tools=self.mcp_tools,  # Use preloaded tools
                checkpointer=memory,
                prompt=self.SYSTEM_INSTRUCTION,
                response_format=(
                    self.RESPONSE_FORMAT_INSTRUCTION,
                    ResponseFormat,
                ),
            )
            logger.debug(
                'LangGraph React agent for Airbnb task created/configured with preloaded tools.'
            )

            config: RunnableConfig = {'configurable': {'thread_id': session_id}}
            langgraph_input = {'messages': [('user', query)]}

            logger.debug(
                f'Invoking Airbnb agent with input: {langgraph_input} and config: {config}'
            )

            await airbnb_agent_runnable.ainvoke(langgraph_input, config)
            logger.debug(
                'Airbnb Agent ainvoke call completed. Fetching response from state...'
            )

            response = self._get_agent_response_from_state(
                config, airbnb_agent_runnable
            )
            logger.info(
                f'Response from Airbnb Agent state for session {session_id}: {response}'
            )
            return response

        except httpx.HTTPStatusError as http_err:
            logger.error(
                f'HTTPStatusError in Airbnb.ainvoke (Airbnb task): {http_err.response.status_code} - {http_err}',
                exc_info=True,
            )
            return {
                'is_task_complete': True,
                'require_user_input': False,
                'content': f'An error occurred with an external service for Airbnb task: {http_err.response.status_code}',
            }
        except Exception as e:
            logger.error(
                f'Unhandled exception in AirbnbAgent.ainvoke (Airbnb task): {type(e).__name__} - {e}',
                exc_info=True,
            )
            # Consider whether to re-raise or return a structured error
            return {
                'is_task_complete': True,  # Or False, marking task as errored
                'require_user_input': False,
                'content': f'An unexpected error occurred while processing your airbnb task: {type(e).__name__}.',
            }
            # Or re-raise if the executor should handle it:
            # raise

    def _get_agent_response_from_state(
        self, config: RunnableConfig, agent_runnable
    ) -> dict[str, Any]:
        """Retrieves and formats the agent's response from the state of the given agent_runnable."""
        logger.debug(
            f'Entering _get_agent_response_from_state for config: {config} using agent: {type(agent_runnable).__name__}'
        )
        try:
            if not hasattr(agent_runnable, 'get_state'):
                logger.error(
                    f'Agent runnable of type {type(agent_runnable).__name__} does not have get_state method.'
                )
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': 'Internal error: Agent state retrieval misconfigured.',
                }

            current_state_snapshot = agent_runnable.get_state(config)
            # The line below caused an error in your original code because .values might not be a dict,
            # but an object from which you access attributes like .values.messages.
            # Let's be more careful accessing it.
            state_values = getattr(current_state_snapshot, 'values', None)
            logger.debug(
                f'Retrieved state snapshot values: {"Available" if state_values else "Not available or None"}'
            )

        except Exception as e:
            logger.error(
                f'Error getting state from agent_runnable ({type(agent_runnable).__name__}): {e}',
                exc_info=True,
            )
            return {
                'is_task_complete': True,
                'require_user_input': False,
                'content': 'Error: Could not retrieve agent state.',
            }

        if not state_values:
            logger.error(
                f'No state values found for config: {config} from agent {type(agent_runnable).__name__}'
            )
            return {
                'is_task_complete': True,
                'require_user_input': False,
                'content': 'Error: Agent state is unavailable.',
            }

        structured_response = (
            state_values.get('structured_response')
            if isinstance(state_values, dict)
            else getattr(state_values, 'structured_response', None)
        )

        if structured_response and isinstance(
            structured_response, ResponseFormat
        ):
            logger.info(
                f'Formatted response from structured_response: {structured_response}'
            )
            if structured_response.status == 'completed':
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': structured_response.message,
                }
            # For 'input_required' or 'error', the task is not complete from user's perspective
            # but might be from the agent's current turn. A2A handles task completion state.
            return {
                'is_task_complete': False,  # Let A2A logic decide based on require_user_input
                'require_user_input': structured_response.status
                == 'input_required',
                'content': structured_response.message,  # This will be the error message if status is 'error'
            }

        # Fallback if structured_response is not as expected
        final_messages = (
            state_values.get('messages', [])
            if isinstance(state_values, dict)
            else getattr(state_values, 'messages', [])
        )

        if final_messages and isinstance(final_messages[-1], AIMessage):
            ai_content = final_messages[-1].content
            if (
                isinstance(ai_content, str) and ai_content
            ):  # Ensure it's a non-empty string
                logger.warning(
                    f'Structured response not found or not in ResponseFormat. Falling back to last AI message content for config {config}.'
                )
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': ai_content,
                }
            if isinstance(
                ai_content, list
            ):  # Handle cases where AIMessage content might be a list of parts (e.g. text and tool calls)
                # Try to extract text content if it's a list of parts
                text_parts = [
                    part['text']
                    for part in ai_content
                    if isinstance(part, dict) and part.get('type') == 'text'
                ]
                if text_parts:
                    logger.warning(
                        f'Structured response not found. Falling back to concatenated text from last AI message parts for config {config}.'
                    )
                    return {
                        'is_task_complete': True,
                        'require_user_input': False,
                        'content': '\n'.join(text_parts),
                    }

        logger.warning(
            f'Structured response not found or not in expected format, and no suitable fallback AI message. State for config {config}: {state_values}'
        )
        return {
            'is_task_complete': False,
            'require_user_input': True,  # Default to needing input or signaling an issue
            'content': 'We are unable to process your request at the moment due to an unexpected response format. Please try again.',
        }

    # stream method would also use self.mcp_tools if it similarly creates an agent instance
    async def stream(self, query: str, session_id: str) -> AsyncIterable[Any]:
        logger.info(
            f"AirbnbAgent.stream called with query: '{query}', sessionId: '{session_id}'"
        )
        agent_runnable = create_react_agent(
            self.model,
            tools=self.mcp_tools,  # Use preloaded tools
            checkpointer=memory,
            prompt=self.SYSTEM_INSTRUCTION,
            response_format=(
                self.RESPONSE_FORMAT_INSTRUCTION,
                ResponseFormat,
            ),  # Ensure final response can be structured
        )
        config: RunnableConfig = {'configurable': {'thread_id': session_id}}
        langgraph_input = {'messages': [('user', query)]}

        logger.debug(
            f'Streaming from Airbnb Agent with input: {langgraph_input} and config: {config}'
        )
        try:
            async for chunk in agent_runnable.astream_events(
                langgraph_input, config, version='v1'
            ):
                logger.debug(f'Stream chunk for {session_id}: {chunk}')
                event_name = chunk.get('event')
                data = chunk.get('data', {})
                content_to_yield = None

                if event_name == 'on_tool_start':
                    tool_name = data.get('name', 'a tool')
                    # tool_input = data.get("input", {}) # Could be verbose
                    content_to_yield = f'Using tool: {tool_name}...'
                elif event_name == 'on_chat_model_stream':
                    message_chunk = data.get('chunk')
                    if (
                        isinstance(message_chunk, AIMessageChunk)
                        and message_chunk.content
                    ):
                        content_to_yield = message_chunk.content

                if content_to_yield:
                    yield {
                        'is_task_complete': False,
                        'require_user_input': False,
                        'content': content_to_yield,
                    }

            # After all events, get the final structured response from the agent's state
            final_response = self._get_agent_response_from_state(
                config, agent_runnable
            )
            logger.info(
                f'Final response from state after stream for session {session_id}: {final_response}'
            )
            yield final_response

        except Exception as e:
            logger.error(
                f'Error during AirbnbAgent.stream for session {session_id}: {e}',
                exc_info=True,
            )
            yield {
                'is_task_complete': True,  # Stream ended due to error
                'require_user_input': False,
                'content': f'An error occurred during streaming: {getattr(e, "message", str(e))}',
            }
