import asyncio
import logging
import os
import time
from collections.abc import AsyncIterable
from typing import Any

from azure.identity.aio import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder
from dotenv import load_dotenv
from pydantic import BaseModel
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentSettings, AzureAIAgentThread
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.mcp import MCPSsePlugin, MCPStdioPlugin
# from semantic_kernel.contents import ChatMessageContent

logger = logging.getLogger(__name__)

load_dotenv()

# region Response Format


class ResponseFormat(BaseModel):
    """A Response Format model to direct how the model should respond."""

    status: str = 'input_required'
    message: str


# endregion

# region Azure AI Agent with MCP


class SemanticKernelMCPAgent:
    """Wraps Azure AI Agent with MCP plugins to handle various tasks."""

    def __init__(self):
        self.agent = None
        self.thread = None
        self.client = None
        self.credential = None
        self.plugin = None

    async def initialize_playwright(self):
        """Initialize the agent with Playwright MCP plugin (following notebook pattern)."""
        try:
            # Create Azure credential
            self.credential = DefaultAzureCredential()
            
            # Create Azure AI client (using async context manager pattern from notebook)
            self.client = await AzureAIAgent.create_client(credential=self.credential).__aenter__()
            
            # Create the Playwright MCP STDIO plugin (following notebook pattern)
            self.plugin = MCPStdioPlugin(
                name="Playwright",
                command="npx",
                args=["@playwright/mcp@latest"],
            )
            
            # Initialize the plugin using async context manager
            await self.plugin.__aenter__()
            
            # Create agent definition (following notebook pattern)
            agent_definition = await self.client.agents.create_agent(
                model=AzureAIAgentSettings().model_deployment_name,
                name="PlayWrightAgent",  # Using same name as notebook
                instructions="Answer the user's questions.",  # Using same instructions as notebook
            )

            # Create the agent with MCP plugin
            self.agent = AzureAIAgent(
                client=self.client,
                definition=agent_definition,
                plugins=[self.plugin],
            )
            
            logger.info("MCP Agent with Playwright plugin initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP Agent with Playwright: {e}")
            await self.cleanup()
            raise

    async def initialize_with_stdio(self, name: str, command: str, args: list[str] = None):
        """Initialize the agent with Azure credentials and MCP STDIO plugin.
        
        Args:
            name: Name of the MCP plugin
            command: Command to start MCP server (e.g., "python", "npx")
            args: Arguments for the command (e.g., ["server.py"] or ["@playwright/mcp@latest"])
        """
        try:
            # Create Azure credential
            self.credential = DefaultAzureCredential()
            
            # Create Azure AI client (using async context manager pattern from notebook)
            self.client = await AzureAIAgent.create_client(credential=self.credential).__aenter__()
            
            # Create the MCP STDIO plugin
            if args:
                self.plugin = MCPStdioPlugin(
                    name=name,
                    command=command,
                    args=args,
                )
            else:
                self.plugin = MCPStdioPlugin(
                    name=name,
                    command=command,
                )
            
            # Initialize the plugin using async context manager
            await self.plugin.__aenter__()
            
            # Create agent definition (following notebook pattern)
            agent_definition = await self.client.agents.create_agent(
                model=AzureAIAgentSettings().model_deployment_name,
                name="SKAssistant",  # Using same name as notebook
                instructions="Answer the user's questions.",  # Using same instructions as notebook
            )

            # Create the agent with MCP plugin
            self.agent = AzureAIAgent(
                client=self.client,
                definition=agent_definition,
                plugins=[self.plugin],
            )
            
            logger.info(f"MCP Agent with STDIO plugin '{name}' initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP Agent with STDIO '{name}': {e}")
            await self.cleanup()
            raise

    async def invoke(self, user_input: str, session_id: str = None) -> dict[str, Any]:
        """Handle tasks with the Azure AI Agent and MCP plugins.

        Args:
            user_input (str): User input message.
            session_id (str): Unique identifier for the session (optional).

        Returns:
            dict: A dictionary containing the content and task completion status.
        """
        if not self.agent:
            return {
                'is_task_complete': False,
                'require_user_input': True,
                'content': 'Agent not initialized. Please call initialize() first.',
            }

        try:
            responses = []
            # Follow the notebook pattern with proper response handling
            async for response in self.agent.invoke(
                messages=user_input,
                thread=self.thread,
            ):
                # Print response as in notebook (for debugging)
                print(f"# {response.name}: {response}")
                responses.append(str(response))
                self.thread = response.thread

            content = "\n".join(responses) if responses else "No response received."
            print("Finished processing user input.")  # Following notebook pattern
            
            return {
                'is_task_complete': True,
                'require_user_input': False,
                'content': content,
            }
        except Exception as e:
            return {
                'is_task_complete': False,
                'require_user_input': True,
                'content': f'Error processing request: {str(e)}',
            }

    async def stream(
        self,
        user_input: str,
        session_id: str = None,
    ) -> AsyncIterable[dict[str, Any]]:
        """Stream responses from the Azure AI Agent with MCP plugins.

        Args:
            user_input (str): User input message.
            session_id (str): Unique identifier for the session (optional).

        Yields:
            dict: A dictionary containing the content and task completion status.
        """
        if not self.agent:
            yield {
                'is_task_complete': False,
                'require_user_input': True,
                'content': 'Agent not initialized. Please call initialize() first.',
            }
            return

        try:
            async for response in self.agent.invoke(
                messages=user_input,
                thread=self.thread,
            ):
                # Print response name as in notebook pattern
                print(f"# {response.name}: {response}")
                self.thread = response.thread
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': str(response),
                }
            
            # Final completion message
            print("Finished processing user input.")  # Following notebook pattern
            yield {
                'is_task_complete': True,
                'require_user_input': False,
                'content': 'Task completed successfully.',
            }
        except Exception as e:
            yield {
                'is_task_complete': False,
                'require_user_input': True,
                'content': f'Error processing request: {str(e)}',
            }

    async def cleanup(self):
        """Cleanup resources."""
        try:
            if self.thread:
                await self.thread.delete()
                self.thread = None
                logger.info("Thread deleted successfully")
        except Exception as e:
            logger.error(f"Error deleting thread: {e}")
        
        try:
            if self.agent and self.client:
                await self.client.agents.delete_agent(self.agent.id)
                logger.info("Agent deleted successfully")
        except Exception as e:
            logger.error(f"Error deleting agent: {e}")
        
        try:
            if self.plugin:
                await self.plugin.__aexit__(None, None, None)
                self.plugin = None
                logger.info("MCP plugin cleaned up successfully")
        except Exception as e:
            logger.error(f"Error cleaning up MCP plugin: {e}")
        
        try:
            if self.client:
                await self.client.close()
                self.client = None
                logger.info("Client closed successfully")
        except Exception as e:
            logger.error(f"Error closing client: {e}")
        
        try:
            if self.credential:
                await self.credential.close()
                self.credential = None
                logger.info("Credential closed successfully")
        except Exception as e:
            logger.error(f"Error closing credential: {e}")
        
        self.agent = None

# endregion

# region Convenience Functions for Notebook-style Usage

async def run_playwright_agent_example(user_input: str = "please navigate to github.com/kinfey"):
    """Run Playwright MCP agent example similar to the updated notebook implementation.
    
    Args:
        user_input: The user input to process
    """
    agent = SemanticKernelMCPAgent()
    
    try:
        # Initialize agent with Playwright plugin
        await agent.initialize_playwright()
        
        # Process user input
        print(f"Processing user input: {user_input}")
        result = await agent.invoke(user_input)
        
        print("\nResult:")
        print(result['content'])
        
        return result
        
    except Exception as e:
        print(f"Error: {e}")
        return {
            'is_task_complete': False,
            'require_user_input': True,
            'content': f'Error: {str(e)}',
        }
    finally:
        # Cleanup
        await agent.cleanup()


async def run_playwright_agent_stream_example(user_input: str = "please navigate to github.com/kinfey"):
    """Run Playwright MCP agent with streaming similar to the updated notebook implementation.
    
    Args:
        user_input: The user input to process
    """
    agent = SemanticKernelMCPAgent()
    
    try:
        # Initialize agent with Playwright plugin
        await agent.initialize_playwright()
        
        # Process user input with streaming
        print(f"Processing user input (streaming): {user_input}")
        
        async for response in agent.stream(user_input):
            if not response['is_task_complete']:
                print(response['content'])
            else:
                print(f"\nFinal result: {response['content']}")
                break
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        await agent.cleanup()

# endregion
