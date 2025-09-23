import logging
import os
from typing import Dict, NoReturn

from dotenv import load_dotenv
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Role, TaskState, TextPart, UnsupportedOperationError
from a2a.utils import new_agent_text_message
from a2a.utils.errors import ServerError
from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_toolset import (
    McpToolset,
    StreamableHTTPConnectionParams,
)
from google.auth import exceptions as google_auth_exceptions
from google.auth.transport import requests as google_auth_requests
from google.genai import types
from google.oauth2 import id_token as google_id_token

# Set logging
logging.getLogger().setLevel(logging.INFO)
load_dotenv()


def get_gcp_auth_headers(audience: str) -> Dict[str, str]:
    """
    Fetches a Google Cloud OIDC token for a target audience using ADC.

    This simplified function relies entirely on Application Default Credentials (ADC)
    and the google-auth library. The library automatically handles checking for
    local credentials, service accounts, or querying the metadata server,
    making a manual fallback unnecessary.

    Args:
        audience: The full URL/URI of the target service (e.g., your Cloud Run URL),
                  which is used as the audience for the OIDC token.

    Returns:
        A dictionary with the "Authorization" header, or an empty
        dictionary if auth fails or is skipped (e.g., no credentials).
    """
    try:
        # This single call is the canonical way to get an OIDC token using ADC.
        # It automatically finds credentials (local, SA, or metadata server).
        auth_req = google_auth_requests.Request()
        token = google_id_token.fetch_id_token(auth_req, audience)

        logging.info("Successfully fetched OIDC token via google.auth.")
        return {"Authorization": f"Bearer {token}"}

    except google_auth_exceptions.DefaultCredentialsError:
        # This is expected in local environments without ADC setup.
        logging.warning(
            "No Google Cloud credentials found (DefaultCredentialsError). "
            "Skipping OIDC token fetch. This is normal for local dev."
        )
        
    except Exception as e:
        # Any other error means ADC was likely found but token minting failed
        # (e.g., IAM permissions, wrong audience, metadata server unreachable).
        logging.critical(
            f"An unexpected error occurred fetching OIDC token for audience '{audience}': {e}",
            exc_info=True
        )

    # Return an empty dict if any exception occurred
    return {}


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
            
            wea_auth_headers = get_gcp_auth_headers(wea_url)

            weather_server_params = StreamableHTTPConnectionParams(
                url=wea_url,
                headers=wea_auth_headers,
            )
  
            # Create the actual agent
            self.agent = LlmAgent(
                model="gemini-2.5-flash",
                name="weather_agent",
                description="An agent that can help questions about weather",
                instruction=f"""You are a specialized weather forecast assistant. Your primary function is to utilize the provided tools to retrieve and relay weather information in response to user queries. You must rely exclusively on these tools for data and refrain from inventing information. Ensure that all responses include the detailed output from the tools used and are formatted in Markdown""",
                tools=[
                    McpToolset(
                        connection_params=weather_server_params,
                      
                    )
                ],
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
        logging.warning(f"Cancellation requested for task {context.task_id}, but not supported.")
        # Inform client that cancellation isn't supported
        raise ServerError(error=UnsupportedOperationError())