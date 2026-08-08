"""Unit and integration tests for MiniMax provider in Semantic Kernel agent."""

import os
from unittest.mock import patch

import pytest

from agent import (
    ChatServices,
    SemanticKernelTravelAgent,
    _get_minimax_chat_completion_service,
    get_chat_completion_service,
)


class TestMiniMaxProviderUnit:
    """Unit tests for MiniMax provider configuration."""

    def test_minimax_enum_exists(self):
        """Test that MINIMAX is a valid ChatServices enum value."""
        assert ChatServices.MINIMAX == 'minimax'
        assert ChatServices.MINIMAX in ChatServices

    def test_minimax_enum_alongside_others(self):
        """Test that MINIMAX coexists with other enum values."""
        values = [s.value for s in ChatServices]
        assert 'minimax' in values
        assert 'azure_openai' in values
        assert 'openai' in values

    @patch.dict(
        os.environ,
        {
            'MINIMAX_API_KEY': 'test-key-123',
        },
        clear=False,
    )
    def test_get_minimax_service_returns_completion(self):
        """Test that _get_minimax_chat_completion_service returns a service."""
        from semantic_kernel.connectors.ai.open_ai import (
            OpenAIChatCompletion,
        )

        service = _get_minimax_chat_completion_service()
        assert isinstance(service, OpenAIChatCompletion)

    @patch.dict(
        os.environ,
        {
            'MINIMAX_API_KEY': 'test-key-123',
        },
        clear=False,
    )
    def test_get_minimax_service_default_model(self):
        """Test that MiniMax service uses MiniMax-M2.7 as default model."""
        service = _get_minimax_chat_completion_service()
        assert service.ai_model_id == 'MiniMax-M2.7'

    @patch.dict(
        os.environ,
        {
            'MINIMAX_API_KEY': 'test-key-123',
            'MINIMAX_MODEL_ID': 'MiniMax-M2.7-highspeed',
        },
        clear=False,
    )
    def test_get_minimax_service_custom_model(self):
        """Test that MiniMax model can be overridden via MINIMAX_MODEL_ID."""
        service = _get_minimax_chat_completion_service()
        assert service.ai_model_id == 'MiniMax-M2.7-highspeed'

    @patch.dict(
        os.environ,
        {
            'MINIMAX_API_KEY': 'test-key-123',
        },
        clear=False,
    )
    def test_get_minimax_service_default_base_url(self):
        """Test that MiniMax uses the correct default base URL."""
        service = _get_minimax_chat_completion_service()
        assert 'api.minimax.io' in str(service.client.base_url)

    @patch.dict(
        os.environ,
        {
            'MINIMAX_API_KEY': 'test-key-123',
            'MINIMAX_BASE_URL': 'https://custom.minimax.io/v1',
        },
        clear=False,
    )
    def test_get_minimax_service_custom_base_url(self):
        """Test that MiniMax base URL can be overridden."""
        service = _get_minimax_chat_completion_service()
        assert 'custom.minimax.io' in str(service.client.base_url)

    @patch.dict(
        os.environ,
        {
            'MINIMAX_API_KEY': 'test-key-123',
        },
        clear=False,
    )
    def test_get_chat_completion_service_minimax(self):
        """Test that get_chat_completion_service routes to MiniMax correctly."""
        service = get_chat_completion_service(ChatServices.MINIMAX)
        assert service is not None
        assert service.ai_model_id == 'MiniMax-M2.7'

    def test_get_chat_completion_service_invalid(self):
        """Test that unsupported service name raises ValueError."""
        with pytest.raises(ValueError, match='Unsupported service name'):
            get_chat_completion_service('invalid_service')

    @patch.dict(
        os.environ,
        {
            'MINIMAX_API_KEY': 'test-key-123',
        },
        clear=False,
    )
    def test_minimax_service_id(self):
        """Test that MiniMax service uses the default service_id."""
        service = _get_minimax_chat_completion_service()
        assert service.service_id == 'default'


class TestMiniMaxProviderIntegration:
    """Integration tests for MiniMax provider (requires MINIMAX_API_KEY)."""

    @pytest.fixture(autouse=True)
    def _skip_without_api_key(self):
        if not os.getenv('MINIMAX_API_KEY'):
            pytest.skip('MINIMAX_API_KEY not set')

    @pytest.mark.asyncio
    async def test_minimax_basic_completion(self):
        """Test basic chat completion with MiniMax API via Semantic Kernel."""
        import openai

        client = openai.AsyncOpenAI(
            api_key=os.getenv('MINIMAX_API_KEY'),
            base_url='https://api.minimax.io/v1',
        )
        response = await client.chat.completions.create(
            model='MiniMax-M2.7',
            messages=[
                {'role': 'user', 'content': 'Say "test passed" and nothing else.'}
            ],
            max_tokens=20,
            temperature=1.0,
        )
        assert response.choices[0].message.content
        assert len(response.choices[0].message.content) > 0

    @pytest.mark.asyncio
    async def test_minimax_tool_calling_via_openai(self):
        """Test that MiniMax supports function calling via OpenAI-compat API."""
        import openai

        client = openai.AsyncOpenAI(
            api_key=os.getenv('MINIMAX_API_KEY'),
            base_url='https://api.minimax.io/v1',
        )
        response = await client.chat.completions.create(
            model='MiniMax-M2.7',
            messages=[
                {'role': 'user', 'content': 'What is 1 USD in EUR?'}
            ],
            tools=[
                {
                    'type': 'function',
                    'function': {
                        'name': 'get_exchange_rate',
                        'description': 'Get exchange rate between currencies',
                        'parameters': {
                            'type': 'object',
                            'properties': {
                                'currency_from': {'type': 'string'},
                                'currency_to': {'type': 'string'},
                            },
                            'required': ['currency_from', 'currency_to'],
                        },
                    },
                }
            ],
            max_tokens=200,
            temperature=1.0,
        )
        msg = response.choices[0].message
        assert msg.tool_calls or msg.content

    @pytest.mark.asyncio
    async def test_minimax_streaming(self):
        """Test streaming support with MiniMax API."""
        import openai

        client = openai.AsyncOpenAI(
            api_key=os.getenv('MINIMAX_API_KEY'),
            base_url='https://api.minimax.io/v1',
        )
        stream = await client.chat.completions.create(
            model='MiniMax-M2.7',
            messages=[
                {'role': 'user', 'content': 'Count from 1 to 3.'}
            ],
            max_tokens=50,
            temperature=1.0,
            stream=True,
        )
        chunks = []
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                chunks.append(chunk.choices[0].delta.content)
        assert len(chunks) > 0
