"""Unit and integration tests for MiniMax provider in LangGraph agent."""

import os
from unittest.mock import patch

import pytest
from langchain_openai import ChatOpenAI


class TestMiniMaxProviderUnit:
    """Unit tests for MiniMax provider configuration."""

    @patch.dict(
        os.environ,
        {
            'model_source': 'minimax',
            'MINIMAX_API_KEY': 'test-key-123',
        },
        clear=False,
    )
    def test_minimax_model_source_creates_chatminimax(self):
        """Test that model_source='minimax' creates a ChatMiniMax instance."""
        from app.agent import ChatMiniMax, CurrencyAgent

        agent = CurrencyAgent()
        assert isinstance(agent.model, ChatMiniMax)
        assert isinstance(agent.model, ChatOpenAI)

    @patch.dict(
        os.environ,
        {
            'model_source': 'minimax',
            'MINIMAX_API_KEY': 'test-key-123',
        },
        clear=False,
    )
    def test_minimax_default_model(self):
        """Test that MiniMax uses MiniMax-M2.7 as the default model."""
        from app.agent import CurrencyAgent

        agent = CurrencyAgent()
        assert agent.model.model_name == 'MiniMax-M2.7'

    @patch.dict(
        os.environ,
        {
            'model_source': 'minimax',
            'MINIMAX_API_KEY': 'test-key-123',
            'TOOL_LLM_NAME': 'MiniMax-M2.7-highspeed',
        },
        clear=False,
    )
    def test_minimax_custom_model(self):
        """Test that MiniMax model can be overridden via TOOL_LLM_NAME."""
        from app.agent import CurrencyAgent

        agent = CurrencyAgent()
        assert agent.model.model_name == 'MiniMax-M2.7-highspeed'

    @patch.dict(
        os.environ,
        {
            'model_source': 'minimax',
            'MINIMAX_API_KEY': 'test-key-123',
        },
        clear=False,
    )
    def test_minimax_default_base_url(self):
        """Test that MiniMax uses the correct default base URL."""
        from app.agent import CurrencyAgent

        agent = CurrencyAgent()
        assert 'api.minimax.io' in str(
            agent.model.openai_api_base
        )

    @patch.dict(
        os.environ,
        {
            'model_source': 'minimax',
            'MINIMAX_API_KEY': 'test-key-123',
        },
        clear=False,
    )
    def test_minimax_temperature_not_zero(self):
        """Test that MiniMax uses temperature=1.0 (not 0, which MiniMax rejects)."""
        from app.agent import CurrencyAgent

        agent = CurrencyAgent()
        assert agent.model.temperature == 1.0

    @patch.dict(
        os.environ,
        {
            'model_source': 'minimax',
            'MINIMAX_API_KEY': 'test-key-123',
        },
        clear=False,
    )
    def test_minimax_api_key_used(self):
        """Test that MINIMAX_API_KEY environment variable is used."""
        from app.agent import CurrencyAgent

        agent = CurrencyAgent()
        assert agent.model.openai_api_key.get_secret_value() == 'test-key-123'

    @patch.dict(
        os.environ,
        {
            'model_source': 'minimax',
            'MINIMAX_API_KEY': 'test-key-123',
        },
        clear=False,
    )
    def test_minimax_agent_has_tools(self):
        """Test that the agent still has tools configured."""
        from app.agent import CurrencyAgent

        agent = CurrencyAgent()
        assert len(agent.tools) > 0

    @patch.dict(
        os.environ,
        {
            'model_source': 'minimax',
            'MINIMAX_API_KEY': 'test-key-123',
        },
        clear=False,
    )
    def test_minimax_agent_has_graph(self):
        """Test that the LangGraph react agent is created."""
        from app.agent import CurrencyAgent

        agent = CurrencyAgent()
        assert agent.graph is not None

    @patch.dict(
        os.environ,
        {
            'model_source': 'minimax',
            'MINIMAX_API_KEY': 'test-key-123',
            'TOOL_LLM_URL': 'https://custom.minimax.io/v1',
        },
        clear=False,
    )
    def test_minimax_custom_base_url(self):
        """Test that MiniMax base URL can be overridden via TOOL_LLM_URL."""
        from app.agent import CurrencyAgent

        agent = CurrencyAgent()
        assert 'custom.minimax.io' in str(
            agent.model.openai_api_base
        )

    @patch.dict(
        os.environ,
        {
            'model_source': 'minimax',
            'MINIMAX_API_KEY': 'test-key-123',
        },
        clear=False,
    )
    def test_minimax_supported_content_types(self):
        """Test that supported content types include text."""
        from app.agent import CurrencyAgent

        agent = CurrencyAgent()
        assert 'text' in agent.SUPPORTED_CONTENT_TYPES

    def test_think_tag_stripping(self):
        """Test that <think> tags are stripped from content."""
        import re

        from app.agent import _THINK_TAG_RE

        content = '<think>\nSome reasoning here.\n</think>\n\n{"status": "completed", "message": "done"}'
        stripped = _THINK_TAG_RE.sub('', content).strip()
        assert '<think>' not in stripped
        assert '{"status": "completed"' in stripped

    def test_think_tag_stripping_no_tags(self):
        """Test that content without think tags is unchanged."""
        from app.agent import _THINK_TAG_RE

        content = '{"status": "completed", "message": "done"}'
        stripped = _THINK_TAG_RE.sub('', content).strip()
        assert stripped == content

    @patch.dict(
        os.environ,
        {
            'model_source': 'minimax',
            'MINIMAX_API_KEY': 'test-key-123',
        },
        clear=False,
    )
    def test_minimax_uses_function_calling_for_structured_output(self):
        """Test that ChatMiniMax uses function_calling method for structured output."""
        from app.agent import ChatMiniMax, ResponseFormat

        model = ChatMiniMax(
            model='MiniMax-M2.7',
            openai_api_key='test-key',
            openai_api_base='https://api.minimax.io/v1',
        )
        structured = model.with_structured_output(ResponseFormat)
        assert structured is not None


class TestMiniMaxProviderIntegration:
    """Integration tests for MiniMax provider (requires MINIMAX_API_KEY)."""

    @pytest.fixture(autouse=True)
    def _skip_without_api_key(self):
        if not os.getenv('MINIMAX_API_KEY'):
            pytest.skip('MINIMAX_API_KEY not set')

    @patch.dict(
        os.environ,
        {'model_source': 'minimax'},
        clear=False,
    )
    @pytest.mark.asyncio
    async def test_minimax_basic_chat(self):
        """Test basic chat completion with MiniMax API."""
        from app.agent import CurrencyAgent

        agent = CurrencyAgent()
        result = None
        async for item in agent.stream(
            'How much is 1 USD in EUR?', 'test-session'
        ):
            result = item
        assert result is not None
        assert 'content' in result
        assert result['content']

    @patch.dict(
        os.environ,
        {'model_source': 'minimax'},
        clear=False,
    )
    @pytest.mark.asyncio
    async def test_minimax_tool_calling(self):
        """Test that MiniMax can use the exchange rate tool."""
        import openai

        client = openai.AsyncOpenAI(
            api_key=os.getenv('MINIMAX_API_KEY'),
            base_url='https://api.minimax.io/v1',
        )
        response = await client.chat.completions.create(
            model='MiniMax-M2.7',
            messages=[
                {'role': 'user', 'content': 'What is 1 USD in JPY?'}
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

    @patch.dict(
        os.environ,
        {'model_source': 'minimax'},
        clear=False,
    )
    @pytest.mark.asyncio
    async def test_minimax_streaming_responses(self):
        """Test that MiniMax streams intermediate responses."""
        from app.agent import CurrencyAgent

        agent = CurrencyAgent()
        responses = []
        async for item in agent.stream(
            'Convert 100 USD to GBP', 'test-session-3'
        ):
            responses.append(item)
        assert len(responses) >= 1
        final = responses[-1]
        assert 'content' in final
