# ruff: noqa: E501
# pylint: disable=logging-fstring-interpolation
import asyncio
import json
import os
import uuid

import httpx

from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    Message,
    Part,
    Role,
    SendMessageConfiguration,
    SendMessageRequest,
    Task,
    TaskState,
)
from a2a.utils.constants import TransportProtocol
from remote_agent_connection import (
    RemoteAgentConnections,
    TaskUpdateCallback,
)
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.tool_context import ToolContext


load_dotenv()


class CoordinatorAgent:
    """The Coordinator agent.

    This is the agent responsible for sending tasks to agents.
    """

    def __init__(
        self,
        task_callback: TaskUpdateCallback | None = None,
    ):
        self.task_callback = task_callback
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ''
        self._httpx_client: httpx.AsyncClient | None = None
        self.client_factory: ClientFactory | None = None

    async def _async_init_components(
        self, remote_agent_addresses: list[str]
    ) -> None:
        """Resolve agent cards during startup using a temporary httpx client.

        The ClientFactory and RemoteAgentConnections are intentionally NOT
        created here because this runs inside asyncio.run(), which closes its
        event loop when done. Any httpx client created here would be bound to
        that dead loop and fail when Gradio's event loop later tries to use it.
        Card resolution only needs the cards, so we use a short-lived client
        that is properly closed before the loop exits.
        """
        async with httpx.AsyncClient(timeout=30) as temp_client:
            for address in remote_agent_addresses:
                card_resolver = A2ACardResolver(temp_client, address)
                try:
                    card = await card_resolver.get_agent_card()
                    self.cards[card.name] = card
                except httpx.ConnectError as e:
                    print(f'ERROR: Failed to get agent card from {address}: {e}')
                except Exception as e:
                    print(
                        f'ERROR: Failed to initialize connection for {address}: {e}'
                    )

        agent_info = []
        for agent_detail_dict in self.list_remote_agents():
            agent_info.append(json.dumps(agent_detail_dict))
        self.agents = '\n'.join(agent_info)

    def _ensure_connections(self) -> None:
        """Lazily create the ClientFactory and agent connections.

        Called on the first send_message so that the httpx client is created
        inside the running event loop (Gradio's), not the init loop.
        """
        if self.client_factory is not None:
            return
        self._httpx_client = httpx.AsyncClient(timeout=30)
        config = ClientConfig(
            httpx_client=self._httpx_client,
            supported_protocol_bindings=[
                TransportProtocol.JSONRPC,
                TransportProtocol.HTTP_JSON,
            ],
        )
        self.client_factory = ClientFactory(config)
        for name, card in self.cards.items():
            self.remote_agent_connections[name] = RemoteAgentConnections(
                client_factory=self.client_factory, agent_card=card
            )

    @classmethod
    async def create(
        cls,
        remote_agent_addresses: list[str],
        task_callback: TaskUpdateCallback | None = None,
    ) -> 'CoordinatorAgent':
        """Create and asynchronously initialize an instance of the CoordinatorAgent."""
        instance = cls(task_callback)
        await instance._async_init_components(remote_agent_addresses)
        return instance

    def create_agent(self) -> Agent:
        """Create an instance of the CoordinatorAgent."""
        model_id = 'gemini-2.5-flash'
        print(f'Using hardcoded model: {model_id}')
        return Agent(
            model=model_id,
            name='Routing_agent',
            instruction=self.root_instruction,
            before_model_callback=self.before_model_callback,
            description=(
                'This coordinator agent orchestrates the content planning and content writing agents'
            ),
            tools=[
                self.send_message,
            ],
        )

    def root_instruction(self, context: ReadonlyContext) -> str:
        """Generate the root instruction for the CoordinatorAgent."""
        current_agent = self.check_active_agent(context)
        return f"""
        **Role:** You are the central content coordination agent. Your primary function is to manage the content creation process.
        Upon receiving a high-level description of content from the user, you will perform the following tasks and then return the
        final polished content:

        Task 1. **Content Planning**
        Task 2. **Content Writing**
        Task 3. **Content Editing**

        **Core Directives:**

        * **Task Delegation:** Utilize the `send_message` function to assign each task to a remote agent.
        * **Contextual Awareness for Remote Agents:** If a remote agent repeatedly requests user confirmation, assume it lacks access to the full conversation history. In such cases, enrich the task description with all necessary contextual information relevant to that specific agent.
        * **Autonomous Agent Engagement:** Never seek user permission before engaging with remote agents. If multiple agents are required to fulfill a request, connect with them directly without requesting user preference or confirmation.
        * **Transparent Communication:** Always present the complete and detailed response from the remote agent to the user.
        * **User Confirmation Relay:** If a remote agent asks for confirmation, and the user has not already provided it, relay this confirmation request to the user.
        * **Focused Information Sharing:** Provide remote agents with only relevant contextual information. Avoid extraneous details.
        * **No Redundant Confirmations:** Do not ask remote agents for confirmation of information or actions.
        * **Tool Reliance:** Strictly rely on available tools to address user requests. Do not generate responses based on assumptions. If information is insufficient, request clarification from the user.
        * **Prioritize Recent Interaction:** Focus primarily on the most recent parts of the conversation when processing requests.
        * **Active Agent Prioritization:** If an active agent is already engaged, route subsequent related requests to that agent using the appropriate task update tool.

        **Agent Roster:**

        * Available Agents: `{self.agents}`
        * Currently Active Agent: `{current_agent['active_agent']}`
                """

    def check_active_agent(self, context: ReadonlyContext):
        state = context.state
        if (
            'session_id' in state
            and 'session_active' in state
            and state['session_active']
            and 'active_agent' in state
        ):
            return {'active_agent': f'{state["active_agent"]}'}
        return {'active_agent': 'None'}

    def before_model_callback(
        self, callback_context: CallbackContext, llm_request
    ):
        state = callback_context.state
        if 'session_active' not in state or not state['session_active']:
            if 'session_id' not in state:
                state['session_id'] = str(uuid.uuid4())
            state['session_active'] = True

    def list_remote_agents(self):
        """List the available remote agents you can use to delegate the task."""
        if not self.cards:
            return []

        remote_agent_info = []
        for card in self.cards.values():
            print(f'Found agent card: name={card.name}')
            print('=' * 100)
            remote_agent_info.append(
                {'name': card.name, 'description': card.description}
            )
        return remote_agent_info

    async def send_message(
        self, agent_name: str, task: str, tool_context: ToolContext
    ):
        """Sends a task to a remote agent.

        Args:
            agent_name: The name of the agent to send the task to.
            task: The comprehensive conversation context summary
                and goal to be achieved regarding user inquiry.
            tool_context: The tool context this method runs in.

        Returns:
            The response text from the remote agent.
        """
        self._ensure_connections()
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f'Agent {agent_name} not found')
        print('sending message to', agent_name)
        state = tool_context.state
        state['active_agent'] = agent_name
        client = self.remote_agent_connections[agent_name]

        if not client:
            raise ValueError(f'Client not available for {agent_name}')

        context_id = state.get('context_id', str(uuid.uuid4()))
        message_id = str(uuid.uuid4())

        request = SendMessageRequest(
            message=Message(
                role=Role.ROLE_USER,
                parts=[Part(text=task)],
                message_id=message_id,
                context_id=context_id,
            ),
            configuration=SendMessageConfiguration(
                accepted_output_modes=['text'],
            ),
        )

        response = await client.send_message(request)
        print('send_response:', response)

        if response is None:
            print('received no response from agent')
            return None

        if isinstance(response, Message):
            result = [
                p.text for p in response.parts
                if p.WhichOneof('content') == 'text'
            ]
            return '\n'.join(result) if result else None

        task_result: Task = response
        if task_result.context_id:
            state['context_id'] = task_result.context_id
        state['task_id'] = task_result.id

        if task_result.status.state == TaskState.TASK_STATE_CANCELED:
            raise ValueError(f'Agent {agent_name} task {task_result.id} is cancelled')
        if task_result.status.state == TaskState.TASK_STATE_FAILED:
            raise ValueError(f'Agent {agent_name} task {task_result.id} failed')
        if task_result.status.state == TaskState.TASK_STATE_INPUT_REQUIRED:
            tool_context.actions.skip_summarization = True
            tool_context.actions.escalate = True

        result = []
        if task_result.status.message.ByteSize() > 0:
            result.extend(
                p.text for p in task_result.status.message.parts
                if p.WhichOneof('content') == 'text'
            )
        for artifact in task_result.artifacts:
            result.extend(
                p.text for p in artifact.parts
                if p.WhichOneof('content') == 'text'
            )
        return '\n'.join(result) if result else None


def _get_initialized_coordinator_agent_sync() -> Agent:
    """Synchronously creates and initializes the CoordinatorAgent."""

    async def _async_main() -> Agent:
        coordinator_agent_instance = await CoordinatorAgent.create(
            remote_agent_addresses=[
                os.getenv('CONTENT_EDITOR_AGENT_URL', 'http://localhost:10003'),
                os.getenv('CONTENT_WRITER_AGENT_URL', 'http://localhost:10002'),
                os.getenv('CONTENT_PLANNER_AGENT_URL', 'http://localhost:10001'),
            ]
        )
        return coordinator_agent_instance.create_agent()

    try:
        return asyncio.run(_async_main())
    except RuntimeError as e:
        if 'asyncio.run() cannot be called from a running event loop' in str(e):
            print(
                f'Warning: Could not initialize CoordinatorAgent with asyncio.run(): {e}. '
                'This can happen if an event loop is already running (e.g., in Jupyter). '
                'Consider initializing CoordinatorAgent within an async function in your application.'
            )
        raise


root_agent = _get_initialized_coordinator_agent_sync()
