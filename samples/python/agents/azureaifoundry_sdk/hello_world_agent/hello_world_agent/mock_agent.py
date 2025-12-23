"""Mock agent for demo mode when Azure credentials are not available."""

import asyncio
import logging
import random
from typing import List

logger = logging.getLogger(__name__)


class MockAgent:
    """Mock agent that simulates Azure AI Foundry agent responses."""
    
    def __init__(self):
        self.agent_id = "mock-agent-123"
        self.threads = {}
        self.responses = [
            "Hello! I'm a mock Azure AI Foundry agent. This is just a demo mode.",
            "I can help you understand how the interface works without needing Azure credentials.",
            "In real mode, I would be powered by Azure AI Foundry and could handle complex conversations.",
            "Try asking me different questions to see various response patterns!",
            "This demo shows the real-time WebSocket communication and UI features.",
            "When you have Azure credentials configured, I'll be much more intelligent!",
            "I can simulate typing delays and multiple response patterns.",
            "The web interface supports markdown, emojis, and real-time updates! 🚀",
            "This is a great way to test the user interface before connecting to Azure.",
            "Thanks for trying out the Hello World Azure AI Foundry Agent demo!"
        ]
        self.question_responses = {
            "hello": "Hello there! Welcome to the demo mode! 👋",
            "help": "I'm a demo agent. I can show you how the interface works without Azure credentials.",
            "what": "I'm a mock version of an Azure AI Foundry agent, running in demo mode.",
            "how": "This demo uses mock responses to simulate real agent behavior.",
            "demo": "Yes, this is demo mode! No Azure credentials required. 🎭",
            "test": "Testing successful! The interface is working perfectly. ✅",
            "thank": "You're welcome! I'm happy to help demonstrate the capabilities! 😊",
            "bye": "Goodbye! Thanks for trying the demo. Have a great day! 👋"
        }

    async def create_agent(self):
        """Mock agent creation."""
        logger.info("Created mock agent in demo mode")
        return self

    async def create_thread(self, thread_id: str = None):
        """Mock thread creation."""
        mock_thread = type('MockThread', (), {'id': f'mock-thread-{len(self.threads)}'})()
        self.threads[mock_thread.id] = mock_thread.id
        logger.info(f"Created mock thread: {mock_thread.id}")
        return mock_thread

    async def run_conversation(self, thread_id: str, user_message: str) -> List[str]:
        """Mock conversation with simulated delay."""
        # Simulate thinking time
        await asyncio.sleep(random.uniform(1, 3))
        
        # Choose response based on user message
        user_lower = user_message.lower()
        response = None
        
        # Check for keyword matches
        for keyword, preset_response in self.question_responses.items():
            if keyword in user_lower:
                response = preset_response
                break
        
        # If no keyword match, use a random response
        if not response:
            response = random.choice(self.responses)
        
        # Sometimes add a follow-up response
        responses = [response]
        if random.random() < 0.3:  # 30% chance of follow-up
            follow_ups = [
                "Is there anything else you'd like to know about the demo?",
                "Feel free to ask me more questions!",
                "The real agent would be even more helpful with Azure AI!",
                "Try different types of messages to see various responses!"
            ]
            responses.append(random.choice(follow_ups))
        
        logger.info(f"Mock agent responded to: {user_message[:50]}...")
        return responses

    async def cleanup_agent(self):
        """Mock cleanup."""
        logger.info("Mock agent cleanup completed")


async def create_mock_agent():
    """Factory function to create a mock agent."""
    agent = MockAgent()
    await agent.create_agent()
    return agent
