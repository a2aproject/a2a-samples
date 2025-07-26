import asyncio
import json
import os
import time
import uuid

from typing import Any, Dict, List, Optional

import httpx

from a2a.client import A2ACardResolver
from a2a.types import (
    AgentCard,
    MessageSendParams,
    Part,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
    TaskState,
)
from remote_agent_connection import (
    RemoteAgentConnections,
    TaskUpdateCallback,
)
from azure.ai.agents import AgentsClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder, ToolSet
from dotenv import load_dotenv


load_dotenv()


class AzureAgentContext:
    """Context class to replace Google ADK ReadonlyContext."""
    def __init__(self):
        self.state: Dict[str, Any] = {}


def convert_part(part: Part) -> str:
    """Convert a part to text. Only text parts are supported."""
    if part.type == 'text':
        return part.text

    return f'Unknown type: {part.type}'


def convert_parts(parts: list[Part]) -> List[str]:
    """Convert parts to text."""
    rval = []
    for p in parts:
        rval.append(convert_part(p))
    return rval


def create_send_message_payload(
    text: str, task_id: str | None = None, context_id: str | None = None
) -> dict[str, Any]:
    """Helper function to create the payload for sending a task."""
    payload: dict[str, Any] = {
        'message': {
            'role': 'user',
            'parts': [{'type': 'text', 'text': text}],
            'messageId': uuid.uuid4().hex,
        },
    }

    if task_id:
        payload['message']['taskId'] = task_id

    if context_id:
        payload['message']['contextId'] = context_id
    return payload


class RoutingAgent:
    """The Routing agent.

    This is the agent responsible for choosing which remote seller agents to send
    tasks to and coordinate their work using Azure AI Agents.
    """

    def __init__(
        self,
        task_callback: TaskUpdateCallback | None = None,
    ):
        self.task_callback = task_callback
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ''
        self.context = AzureAgentContext()
        
        # Initialize Azure AI Agents client
        self.agents_client = AgentsClient(
            endpoint=os.environ["AZURE_AI_AGENT_ENDPOINT"],
            credential=DefaultAzureCredential(),
        )
        self.azure_agent = None
        self.current_thread = None

    async def _async_init_components(
        self, remote_agent_addresses: list[str]
    ) -> None:
        """Asynchronous part of initialization."""
        # Use a single httpx.AsyncClient for all card resolutions for efficiency
        async with httpx.AsyncClient(timeout=30) as client:
            for address in remote_agent_addresses:
                card_resolver = A2ACardResolver(
                    client, address
                )  # Constructor is sync
                try:
                    card = (
                        await card_resolver.get_agent_card()
                    )  # get_agent_card is async

                    remote_connection = RemoteAgentConnections(
                        agent_card=card, agent_url=address
                    )
                    self.remote_agent_connections[card.name] = remote_connection
                    self.cards[card.name] = card
                except httpx.ConnectError as e:
                    print(
                        f'ERROR: Failed to get agent card from {address}: {e}'
                    )
                except Exception as e:  # Catch other potential errors
                    print(
                        f'ERROR: Failed to initialize connection for {address}: {e}'
                    )

        # Populate self.agents using the logic from original __init__ (via list_remote_agents)
        agent_info = []
        for agent_detail_dict in self.list_remote_agents():
            agent_info.append(json.dumps(agent_detail_dict))
        self.agents = '\n'.join(agent_info)

    @classmethod
    async def create(
        cls,
        remote_agent_addresses: list[str],
        task_callback: TaskUpdateCallback | None = None,
    ) -> 'RoutingAgent':
        """Create and asynchronously initialize an instance of the RoutingAgent."""
        instance = cls(task_callback)
        await instance._async_init_components(remote_agent_addresses)
        return instance

    def create_agent(self):
        """Create an Azure AI Agent instance."""
        instructions = self.get_root_instruction()
        
        try:
            # Create Azure AI Agent with better error handling
            model_name = os.environ.get("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME", "gpt-4")
            print(f"Creating agent with model: {model_name}")
            print(f"Instructions length: {len(instructions)} characters")

            # Create tool definition for send_message function
            from azure.ai.agents.models import FunctionTool

            tools = [{
                "type": "function",
                "function": {
                    "name": "send_message",
                    "description": "Sends a task to a remote seller agent",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "agent_name": {
                                "type": "string",
                                "description": "The name of the agent to send the task to"
                            },
                            "task": {
                                "type": "string",
                                "description": "The comprehensive conversation context summary and goal to be achieved"
                            }
                        },
                        "required": ["agent_name", "task"]
                    }
                }
            }]
 

            # toolset = ToolSet()
            # toolset.add(send_message_tool)
            
            self.azure_agent = self.agents_client.create_agent(
                model=model_name,
                name="routing-agent",
                instructions=instructions,
                tools=tools
            )
            print(f"Created Azure AI agent, agent ID: {self.azure_agent.id}")
            
            # Create a thread for conversation
            self.current_thread = self.agents_client.threads.create()
            print(f"Created thread, thread ID: {self.current_thread.id}")
            
            return self.azure_agent
            
        except Exception as e:
            print(f"Error creating Azure AI agent: {e}")
            print(f"Model name used: {model_name}")
            print(f"Instructions: {instructions[:200]}...")
            raise

    def get_root_instruction(self) -> str:
        """Generate the root instruction for the RoutingAgent."""
        current_agent = self.check_active_agent()
        return f"""You are an expert Routing Delegator that helps users with weather and accommodation requests.

Your role:
- Delegate user inquiries to appropriate specialized remote agents
- Provide clear and helpful responses to users
- Connect users with weather agents for weather inquiries
- Connect users with accommodation agents for booking requests

Available Agents: {self.agents}
Currently Active Agent: {current_agent['active_agent']}

Always be helpful and route requests to the most appropriate agent."""

    def check_active_agent(self):
        """Check the currently active agent."""
        state = self.context.state
        if (
            'session_id' in state
            and 'session_active' in state
            and state['session_active']
            and 'active_agent' in state
        ):
            return {'active_agent': f'{state["active_agent"]}'}
        return {'active_agent': 'None'}

    def initialize_session(self):
        """Initialize a new session."""
        state = self.context.state
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
            print(f'Found agent card: {card.model_dump(exclude_none=True)}')
            print('=' * 100)
            remote_agent_info.append(
                {'name': card.name, 'description': card.description}
            )
        return remote_agent_info

    async def send_message(
        self, agent_name: str, task: str
    ):
        """Sends a task to remote seller agent.

        This will send a message to the remote agent named agent_name.

        Args:
            agent_name: The name of the agent to send the task to.
            task: The comprehensive conversation context summary
                and goal to be achieved regarding user inquiry and purchase request.

        Returns:
            A Task object from the remote agent response.
        """
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f'Agent {agent_name} not found')
        
        state = self.context.state
        state['active_agent'] = agent_name
        client = self.remote_agent_connections[agent_name]

        if not client:
            raise ValueError(f'Client not available for {agent_name}')
        
        task_id = state['task_id'] if 'task_id' in state else str(uuid.uuid4())

        if 'context_id' in state:
            context_id = state['context_id']
        else:
            context_id = str(uuid.uuid4())

        message_id = ''
        metadata = {}
        if 'input_message_metadata' in state:
            metadata.update(**state['input_message_metadata'])
            if 'message_id' in state['input_message_metadata']:
                message_id = state['input_message_metadata']['message_id']
        if not message_id:
            message_id = str(uuid.uuid4())

        payload = {
            'message': {
                'role': 'user',
                'parts': [
                    {'type': 'text', 'text': task}
                ],  # Use the 'task' argument here
                'messageId': message_id,
            },
        }

        if task_id:
            payload['message']['taskId'] = task_id

        if context_id:
            payload['message']['contextId'] = context_id

        message_request = SendMessageRequest(
            id=message_id, params=MessageSendParams.model_validate(payload)
        )
        send_response: SendMessageResponse = await client.send_message(
            message_request=message_request
        )
        print('send_response', send_response.model_dump_json(exclude_none=True, indent=2))

        if not isinstance(send_response.root, SendMessageSuccessResponse):
            print('received non-success response. Aborting get task ')
            return

        if not isinstance(send_response.root.result, Task):
            print('received non-task response. Aborting get task ')
            return

        return send_response.root.result

    async def process_user_message(self, user_message: str) -> str:
        """Process a user message through Azure AI Agent and return the response."""
        if not hasattr(self, 'azure_agent') or not self.azure_agent:
            return "Azure AI Agent not initialized. Please ensure the agent is properly created."
        
        if not hasattr(self, 'current_thread') or not self.current_thread:
            return "Azure AI Thread not initialized. Please ensure the agent is properly created."
        
        try:
            # Initialize session if needed
            self.initialize_session()
            
            print(f"Processing message: {user_message[:50]}...")
            
            # Create message in the thread
            message = self.agents_client.messages.create(
                thread_id=self.current_thread.id, 
                role="user", 
                content=user_message
            )
            print(f"Created message, message ID: {message.id}")

            # Create and run the agent
            print(f"Creating run with agent ID: {self.azure_agent.id}")
            run = self.agents_client.runs.create(
                thread_id=self.current_thread.id, 
                agent_id=self.azure_agent.id
            )
            print(f"Created run, run ID: {run.id}")

            # Poll the run until completion
            max_iterations = 60  # 60 seconds timeout
            iteration = 0
            while run.status in ["queued", "in_progress", "requires_action"] and iteration < max_iterations:
                # Handle function calls if needed
                if run.status == "requires_action":
                    await self._handle_required_actions(run)
                
                time.sleep(1)
                iteration += 1
                run = self.agents_client.runs.get(
                    thread_id=self.current_thread.id, 
                    run_id=run.id
                )
                print(f"Run status: {run.status} (iteration {iteration})")

            if iteration >= max_iterations:
                return "Request timed out after 60 seconds. Please try again."

            if run.status == "failed":
                error_info = f"Run error: {run.last_error}"
                print(error_info)
                
                # Try to get more detailed error information
                if hasattr(run, 'last_error') and run.last_error:
                    if hasattr(run.last_error, 'code'):
                        error_info += f" (Code: {run.last_error.code})"
                    if hasattr(run.last_error, 'message'):
                        error_info += f" (Message: {run.last_error.message})"
                
                return f"Error processing request: {error_info}"

            # Get the latest messages
            messages = self.agents_client.messages.list(
                thread_id=self.current_thread.id, 
                order=ListSortOrder.DESCENDING
            )
            
            # Return the assistant's response
            for msg in messages:
                if msg.role == "assistant" and msg.text_messages:
                    last_text = msg.text_messages[-1]
                    return last_text.text.value
            
            return "No response received from agent."
            
        except Exception as e:
            error_msg = f"Error in process_user_message: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return f"An error occurred while processing your message: {str(e)}"

    async def _handle_required_actions(self, run):
        """Handle function calls required by the Azure AI Agent."""
        try:
            if hasattr(run, 'required_action') and run.required_action:
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    print(f"Executing function: {function_name} with args: {function_args}")
                    
                    if function_name == "send_message":
                        try:
                            # Call our send_message method
                            result = await self.send_message(
                                agent_name=function_args["agent_name"],
                                task=function_args["task"]
                            )
                            # Convert result to JSON string
                            output = json.dumps(result.model_dump() if hasattr(result, 'model_dump') else str(result))
                        except Exception as e:
                            output = json.dumps({"error": str(e)})
                    else:
                        output = json.dumps({"error": f"Unknown function: {function_name}"})
                    
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": output
                    })
                
                # Submit the tool outputs
                self.agents_client.runs.submit_tool_outputs(
                    thread_id=self.current_thread.id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
                print(f"Submitted {len(tool_outputs)} tool outputs")
                
        except Exception as e:
            print(f"Error handling required actions: {e}")
            import traceback
            traceback.print_exc()

    def cleanup(self):
        """Clean up Azure AI agent resources."""
        try:
            if hasattr(self, 'azure_agent') and self.azure_agent and hasattr(self, 'agents_client') and self.agents_client:
                self.agents_client.delete_agent(self.azure_agent.id)
                print(f"Deleted Azure AI agent: {self.azure_agent.id}")
        except Exception as e:
            print(f"Error cleaning up agent: {e}")
        finally:
            # Close the client to clean up resources
            if hasattr(self, 'agents_client') and self.agents_client:
                try:
                    self.agents_client.close()
                    print("Azure AI client closed")
                except Exception as e:
                    print(f"Error closing client: {e}")
            
            if hasattr(self, 'azure_agent'):
                self.azure_agent = None
            if hasattr(self, 'current_thread'):
                self.current_thread = None

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


def _get_initialized_routing_agent_sync() -> RoutingAgent:
    """Synchronously creates and initializes the RoutingAgent."""

    async def _async_main() -> RoutingAgent:
        routing_agent_instance = await RoutingAgent.create(
            remote_agent_addresses=[
                os.getenv('TOOL_AGENT_URL', 'http://localhost:10002'),
                os.getenv('PLAYWRIGHT_AGENT_URL', 'http://localhost:10001'),
            ]
        )
        # Create the Azure AI agent
        routing_agent_instance.create_agent()
        return routing_agent_instance

    try:
        return asyncio.run(_async_main())
    except RuntimeError as e:
        if 'asyncio.run() cannot be called from a running event loop' in str(e):
            print(
                f'Warning: Could not initialize RoutingAgent with asyncio.run(): {e}. '
                'This can happen if an event loop is already running (e.g., in Jupyter). '
                'Consider initializing RoutingAgent within an async function in your application.'
            )
        raise


# Initialize the routing agent
routing_agent = _get_initialized_routing_agent_sync()
