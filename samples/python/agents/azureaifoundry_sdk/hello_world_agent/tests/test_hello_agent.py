"""Tests for the Hello World Azure AI Foundry Agent."""

import os
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add the parent directory to the Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from hello_world_agent.hello_agent import HelloWorldAgent


class TestHelloWorldAgent:
    """Test cases for the HelloWorldAgent."""

    @pytest.fixture
    def mock_env_vars(self):
        """Mock environment variables for testing."""
        with patch.dict(os.environ, {
            'AZURE_AI_FOUNDRY_PROJECT_ENDPOINT': 'https://test-endpoint.com/',
            'AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME': 'test-model'
        }):
            yield

    @pytest.fixture
    def agent(self, mock_env_vars):
        """Create a HelloWorldAgent instance for testing."""
        return HelloWorldAgent()

    def test_init(self, agent):
        """Test agent initialization."""
        assert agent.endpoint == 'https://test-endpoint.com/'
        assert agent.agent is None
        assert agent.threads == {}

    def test_get_instructions(self, agent):
        """Test that instructions are properly formatted."""
        instructions = agent._get_instructions()
        assert isinstance(instructions, str)
        assert len(instructions) > 0
        assert "Hello World agent" in instructions
        assert "friendly" in instructions.lower()

    @patch('hello_agent.AgentsClient')
    @patch('hello_agent.DefaultAzureCredential')
    async def test_create_agent(self, mock_credential, mock_client_class, agent):
        """Test agent creation."""
        # Mock the client and its methods
        mock_client = Mock()
        mock_agent = Mock()
        mock_agent.id = 'test-agent-id'
        mock_client.create_agent.return_value = mock_agent
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Create the agent
        result = await agent.create_agent()

        # Verify the result
        assert result == mock_agent
        assert agent.agent == mock_agent
        mock_client.create_agent.assert_called_once()

    @patch('hello_agent.AgentsClient')
    @patch('hello_agent.DefaultAzureCredential')
    async def test_create_thread(self, mock_credential, mock_client_class, agent):
        """Test thread creation."""
        # Mock the client and its methods
        mock_client = Mock()
        mock_thread = Mock()
        mock_thread.id = 'test-thread-id'
        mock_client.threads.create.return_value = mock_thread
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Create the thread
        result = await agent.create_thread()

        # Verify the result
        assert result == mock_thread
        assert 'test-thread-id' in agent.threads
        mock_client.threads.create.assert_called_once()

    @patch('hello_agent.AgentsClient')
    @patch('hello_agent.DefaultAzureCredential')
    async def test_send_message(self, mock_credential, mock_client_class, agent):
        """Test sending a message."""
        # Mock the client and its methods
        mock_client = Mock()
        mock_message = Mock()
        mock_message.id = 'test-message-id'
        mock_client.messages.create.return_value = mock_message
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Send a message
        result = await agent.send_message('test-thread-id', 'Hello!')

        # Verify the result
        assert result == mock_message
        mock_client.messages.create.assert_called_once_with(
            thread_id='test-thread-id',
            role='user',
            content='Hello!'
        )

    @pytest.mark.asyncio
    async def test_cleanup_agent_no_agent(self, agent):
        """Test cleanup when no agent exists."""
        # This should not raise an exception
        await agent.cleanup_agent()
        assert agent.agent is None


class TestAgentIntegration:
    """Integration tests for the agent (require actual Azure credentials)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """Test a complete conversation flow (requires real credentials)."""
        pytest.skip("Integration test requires real Azure credentials")
        
        # This test would require actual Azure credentials and would look like:
        # agent = HelloWorldAgent()
        # await agent.create_agent()
        # thread = await agent.create_thread()
        # response = await agent.run_conversation(thread.id, "Hello!")
        # assert len(response) > 0
        # await agent.cleanup_agent()


if __name__ == "__main__":
    pytest.main([__file__])
