"""Simple Hello World Azure AI Foundry Agent.

This module provides a minimal example of an Azure AI Foundry agent
that can respond to basic greetings and demonstrate conversation flow.
"""

import asyncio
import logging
import os
import time
from typing import Any

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    Agent,
    AgentThread,
    ListSortOrder,
    ThreadMessage,
    ThreadRun,
)
from azure.identity import DefaultAzureCredential


logger = logging.getLogger(__name__)


class HelloWorldAgent:
    """A simple Hello World agent using Azure AI Foundry.
    
    This agent demonstrates the basic structure and functionality
    of an Azure AI Foundry agent with minimal complexity.
    """

    def __init__(self) -> None:
        """Initialize the Hello World agent."""
        self.endpoint = os.environ["AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"]
        self.credential = DefaultAzureCredential()
        self.agent: Agent | None = None
        self.threads: dict[str, str] = {}

    def _get_client(self) -> AgentsClient:
        """Get a new AgentsClient instance."""
        return AgentsClient(
            endpoint=self.endpoint,
            credential=self.credential,
        )

    async def create_agent(self) -> Agent:
        """Create the Hello World agent."""
        if self.agent:
            return self.agent

        with self._get_client() as client:
            self.agent = client.create_agent(
                model=os.environ["AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"],
                name="hello-world-agent",
                instructions=self._get_instructions(),
            )
            logger.info(f"Created Hello World agent: {self.agent.id}")
            return self.agent

    def _get_instructions(self) -> str:
        """Get the agent instructions."""
        return """
You are a friendly Hello World agent powered by Azure AI Foundry.

Your purpose is to:
- Greet users warmly
- Provide simple, helpful responses
- Demonstrate basic conversation capabilities
- Be encouraging and positive

Keep your responses concise and friendly. When users say hello, greet them back.
When they ask what you can do, explain that you're a simple demo agent that can
have basic conversations and answer simple questions.

Always be polite, helpful, and maintain a positive tone.
"""

    async def create_thread(self, thread_id: str | None = None) -> AgentThread:
        """Create or retrieve a conversation thread."""
        if thread_id and thread_id in self.threads:
            # For simplicity, we'll create a new thread each time
            pass

        with self._get_client() as client:
            thread = client.threads.create()
            self.threads[thread.id] = thread.id
            logger.info(f"Created thread: {thread.id}")
            return thread

    async def send_message(
        self, thread_id: str, content: str, role: str = "user"
    ) -> ThreadMessage:
        """Send a message to the conversation thread."""
        with self._get_client() as client:
            message = client.messages.create(
                thread_id=thread_id, role=role, content=content
            )
            logger.info(f"Created message in thread {thread_id}: {message.id}")
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
            max_iterations = 30
            iterations = 0

            while (
                run.status in ["queued", "in_progress", "requires_action"]
                and iterations < max_iterations
            ):
                iterations += 1
                time.sleep(1)
                run = client.runs.get(thread_id=thread_id, run_id=run.id)
                logger.debug(f"Run status: {run.status} (iteration {iterations})")

                if run.status == "failed":
                    logger.error(f"Run failed during polling: {run.last_error}")
                    break

                # Note: This simple agent doesn't use tools, so no action handling needed

            if run.status == "failed":
                logger.error(f"Run failed: {run.last_error}")
                return [f"Error: {run.last_error}"]

            if iterations >= max_iterations:
                logger.error(f"Run timed out after {max_iterations} iterations")
                return ["Error: Request timed out"]

            # Get response messages
            messages = client.messages.list(
                thread_id=thread_id, order=ListSortOrder.DESCENDING
            )

            responses = []
            for msg in messages:
                if msg.role == "assistant" and msg.text_messages:
                    for text_msg in msg.text_messages:
                        responses.append(text_msg.text.value)
                    break  # Only get the latest assistant response

            return responses if responses else ["No response received"]

    async def cleanup_agent(self) -> None:
        """Clean up the agent resources."""
        if self.agent:
            with self._get_client() as client:
                client.delete_agent(self.agent.id)
                logger.info(f"Deleted agent: {self.agent.id}")
                self.agent = None


async def create_hello_world_agent() -> HelloWorldAgent:
    """Factory function to create and initialize a Hello World agent."""
    agent = HelloWorldAgent()
    await agent.create_agent()
    return agent


# Example usage for testing
async def demo_interaction() -> None:
    """Demo function showing how to use the Hello World agent."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    agent = await create_hello_world_agent()

    try:
        # Create a conversation thread
        thread = await agent.create_thread()

        # Example interactions
        test_messages = [
            "Hello!",
            "What can you do?",
            "Tell me a fun fact",
            "Thank you!",
        ]

        print("🤖 Hello World Azure AI Foundry Agent Demo")
        print("=" * 50)

        for message in test_messages:
            print(f"\n👤 User: {message}")
            responses = await agent.run_conversation(thread.id, message)
            for response in responses:
                print(f"🤖 Assistant: {response}")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"❌ Error: {e}")
    finally:
        await agent.cleanup_agent()


if __name__ == "__main__":
    asyncio.run(demo_interaction())
