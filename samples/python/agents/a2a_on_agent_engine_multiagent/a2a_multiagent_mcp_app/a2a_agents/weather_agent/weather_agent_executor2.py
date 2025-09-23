import base64
import json
import logging
import os
import time
from typing import Dict, List, NoReturn, Optional

import google.auth.transport.requests
import google.oauth2.id_token
import jwt
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Role, TaskState, TextPart, UnsupportedOperationError
from a2a.utils import new_agent_text_message
from a2a.utils.errors import ServerError
from dotenv import load_dotenv
from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.mcp_tool.mcp_session_manager import retry_on_closed_resource
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StreamableHTTPConnectionParams,
)
from google.auth import exceptions as google_auth_exceptions
from google.genai import types


def decode_jwt_no_verify(token: str) -> dict:
    """Decode a JWT token's payload without verifying signature.

    This helper is intentionally lightweight and only used for reading
    untrusted tokens where signature verification is not required.
    It returns the payload as a dict or raises ValueError on malformed tokens.
    """
    try:
        parts = token.split(".")
        if len(parts) < 2:
            raise ValueError("Invalid JWT token format")
        payload_b64 = parts[1]
        # Pad base64 if necessary
        padding = "=" * (-len(payload_b64) % 4)
        payload_b64 += padding
        decoded = base64.urlsafe_b64decode(payload_b64)
        return json.loads(decoded)
    except Exception as e:
        raise ValueError(f"Failed to decode JWT payload: {e}") from e

toolset_cache = {}

# Set logging
logging.getLogger().setLevel(logging.INFO)
load_dotenv()


def get_auth_token(callback_context: CallbackContext) -> Optional[types.Content]:
    # We have only one tool set otherwise you can iterate.
    mcp_toolset = callback_context._invocation_context.agent.tools[0]
    if mcp_toolset._tool_set_name not in toolset_cache:
        toolset_cache[mcp_toolset._tool_set_name] = {}

    # The following means the token was never added to the toolset
    # The headers reset every time so cannot check for headers.
    if "token_expiration_time" not in toolset_cache[mcp_toolset._tool_set_name]:
        logging.info("Getting a token and adding to X-Serverless-Authorization header")
        mcp_toolset._connection_params.headers = {}
        id_token = get_id_token(
            os.environ.get("MCP_SERVER_URL", "http://localhost:8080")
        )
        mcp_toolset._connection_params.headers["X-Serverless-Authorization"] = (
            f"Bearer {id_token}"
        )
        logging.debug(f"id_token => {id_token}")
        try:
            # Prefer PyJWT decode if available
            if hasattr(jwt, "decode"):
                decoded_payload = jwt.decode(id_token, options={"verify_signature": False})
            else:
                decoded_payload = decode_jwt_no_verify(id_token)
        except Exception:
            # Fallback to local decoder
            decoded_payload = decode_jwt_no_verify(id_token)
        logging.debug("Decoded Token:", decoded_payload)
        toolset_cache[mcp_toolset._tool_set_name][
            "prev_used_token"
        ] = f"Bearer {id_token}"
        toolset_cache[mcp_toolset._tool_set_name]["token_expiration_time"] = (
            decoded_payload["exp"]
        )
    else:
        # header is present but the token might be expired or about to expire within the next 15 minutes.
        time_after_threshold_minutes = (
            int(time.time())
            + int(os.environ.get("TOKEN_REFRESH_THRESHOLD_MINS", "15")) * 60
        )
        logging.debug(
            f"Token expires at {toolset_cache[mcp_toolset._tool_set_name]['token_expiration_time']}, Time after 15 minutes = {time_after_threshold_minutes}"
        )
        # instead of decoding the token everytime - we are using the stored value to optimize
        if (
            time_after_threshold_minutes
            >= toolset_cache[mcp_toolset._tool_set_name]["token_expiration_time"]
        ):
            logging.info(f"Getting a new token and updating the cache")
            id_token = get_id_token(
                os.environ.get("MCP_SERVER_URL", "http://localhost:8080")
            )
            mcp_toolset._connection_params.headers = {}
            mcp_toolset._connection_params.headers["X-Serverless-Authorization"] = (
                f"Bearer {id_token}"
            )
            try:
                if hasattr(jwt, "decode"):
                    decoded_payload = jwt.decode(id_token, options={"verify_signature": False})
                else:
                    decoded_payload = decode_jwt_no_verify(id_token)
            except Exception:
                decoded_payload = decode_jwt_no_verify(id_token)
            logging.debug("Decoded Token:", decoded_payload)
            toolset_cache[mcp_toolset._tool_set_name][
                "prev_used_token"
            ] = f"Bearer {id_token}"
            toolset_cache[mcp_toolset._tool_set_name]["token_expiration_time"] = (
                decoded_payload["exp"]
            )
        else:
            logging.error("Using a valid old token")
            mcp_toolset._connection_params.headers = {}
            mcp_toolset._connection_params.headers["X-Serverless-Authorization"] = (
                toolset_cache[mcp_toolset._tool_set_name]["prev_used_token"]
            )

    return None


def get_id_token(audience):
    auth_req = google.auth.transport.requests.Request()
    id_token = google.oauth2.id_token.fetch_id_token(auth_req, audience)
    return id_token


class MCPToolsetWithToolAccess(MCPToolset):
    """
    A subclass of MCPToolset that overrides the get_tools method
    to inject additional information.
    """

    def __init__(self, *args, tool_set_name: str, **kwargs):
        """Initializes MCPToolsetWithToolAccess with a new tool_set_name property."""
        super().__init__(*args, **kwargs)
        self._tool_set_name = tool_set_name

    @retry_on_closed_resource
    async def get_tools(
        self,
        readonly_context: Optional[ReadonlyContext] = None,
    ) -> List[BaseTool]:

        tools = None

        if "tools" not in toolset_cache[self._tool_set_name]:
            # Call the original get_tools method from the parent class
            logging.error(
                f"Did not find tools for the toolset {self._tool_set_name} in cache"
            )
            original_tools = await super().get_tools(readonly_context)

            logging.error(
                f"Start - Fetched tools for {self._tool_set_name} and added to the cache"
            )
            toolset_cache[self._tool_set_name]["tools"] = original_tools
            logging.error(
                f"Done - Fetched tools for {self._tool_set_name} and added to the cache"
            )
            tools = original_tools
        else:
            logging.error(f"Found tools for the toolset {self._tool_set_name} in cache")
            tools = toolset_cache[self._tool_set_name]["tools"]

        return tools


class WeatherAgentExecutor(AgentExecutor):
    """Agent Executor that bridges A2A protocol with our ADK agent.

    The executor handles:
    1. Protocol translation (A2A messages to/from agent format)
    2. Task lifecycle management (submitted -> working -> completed)
    3. Session management for multi-turn conversations
    4. Error handling and recovery
    """

    def __init__(self) -> None:
        """Initialize with lazy loading pattern."""
        self.agent = None
        self.runner = None

    def _init_agent(self) -> None:
        """
        Lazy initialization of agent resources.
        This now constructs the agent and its serializable auth.
        """
        if self.agent is None:
            # --- Environment setup ---
            wea_url = os.getenv("MCP_SERVER_URL")


            weather_server_params = StreamableHTTPConnectionParams(
                url=wea_url,
                timeout=60,
            )

            # Create the actual agent
            self.agent = LlmAgent(
                model="gemini-2.5-flash",
                name="weather_agent",
                description="An agent that can help questions about weather",
                instruction="""You are a specialized weather forecast assistant. Your primary function is to utilize the provided tools to retrieve and relay weather information in response to user queries. You must rely exclusively on these tools for data and refrain from inventing information. Ensure that all responses include the detailed output from the tools used and are formatted in Markdown""",
                tools=[
                    MCPToolsetWithToolAccess(
                        connection_params=StreamableHTTPConnectionParams(
                            url=os.environ.get(
                                "MCP_SERVER_URL", "http://localhost:8080"
                            )
                            + "/mcp",
                            timeout=60,
                        ),
                        tool_set_name="weather_toolset",
                    ),
                ],
                before_agent_callback=get_auth_token,
            )

            # The Runner orchestrates the agent execution
            # It manages the LLM calls, tool execution, and state
            self.runner = Runner(
                app_name=self.agent.name,
                agent=self.agent,
                # In-memory services for simplicity
                # In production, you might use persistent storage
                artifact_service=InMemoryArtifactService(),
                session_service=InMemorySessionService(),
                memory_service=InMemoryMemoryService(),
            )

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Process a user query and return the answer.

        This method is called by the A2A protocol handler when:
        1. A new message arrives (message/send)
        2. A streaming request is made (message/stream)
        """
        # Initialize agent on first call
        if self.agent is None:
            self._init_agent()

        # Extract the user's question from the protocol message
        query = context.get_user_input()
        logging.info(f"Received query: {query}")

        # Create a TaskUpdater for managing task state
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)

        # Update task status through its lifecycle
        # submitted -> working -> completed/failed
        if not context.current_task:
            # New task - mark as submitted
            await updater.submit()

        # Mark task as working (processing)
        await updater.start_work()

        try:
            # Get or create a session for this conversation
            session = await self._get_or_create_session(context.context_id)
            logging.info(f"Using session: {session.id}")

            # Prepare the user message in ADK format
            content = types.Content(role=Role.user, parts=[types.Part(text=query)])

            # Run the agent asynchronously
            # This may involve multiple LLM calls and tool uses
            async for event in self.runner.run_async(
                session_id=session.id,
                user_id="user",  # In production, use actual user ID
                new_message=content,
            ):
                # The agent may produce multiple events
                # We're interested in the final response
                if event.is_final_response():
                    # Extract the answer text from the response
                    answer = self._extract_answer(event)
                    logging.info(f" {answer}")

                    # Add the answer as an artifact
                    # Artifacts are the "outputs" or "results" of a task
                    # They're separate from status messages
                    await updater.add_artifact(
                        [TextPart(text=answer)],
                        name="answer",  # Name helps clients identify artifacts
                    )

                    # Mark task as completed successfully
                    await updater.complete()
                    break


        except Exception as e:
            # Errors should never pass silently (Zen of Python)
            # Always inform the client when something goes wrong
            logging.error(f"Error during execution: {e!s}", exc_info=True)
            await updater.update_status(
                TaskState.failed, message=new_agent_text_message(f"Error: {e!s}")
            )
            # Re-raise for proper error handling up the stack
            raise

    async def _get_or_create_session(self, context_id: str):
        """Get existing session or create new one."""
        session = await self.runner.session_service.get_session(
            app_name=self.runner.app_name,
            user_id="user",
            session_id=context_id,
        )

        if not session:
            logging.info(f"No session found for {context_id}, creating new one.")
            session = await self.runner.session_service.create_session(
                app_name=self.runner.app_name,
                user_id="user",
                session_id=context_id,
            )
        else:
            logging.info(f"Found existing session {context_id}.")

        return session

    def _extract_answer(self, event) -> str:
        """Extract text answer from agent response."""
        parts = event.content.parts
        text_parts = [part.text for part in parts if part.text]

        # Join all text parts with space
        return " ".join(text_parts) if text_parts else "No answer found."

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> NoReturn:
        """Handle task cancellation requests.

        For long-running agents, this would:
        1. Stop any ongoing processing
        2. Clean up resources
        3. Update task state to 'cancelled'
        """
        logging.warning(
            f"Cancellation requested for task {context.task_id}, but not supported."
        )
        # Inform client that cancellation isn't supported
        raise ServerError(error=UnsupportedOperationError())
