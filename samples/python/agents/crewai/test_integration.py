"""Integration tests for CrewAI Image Generation Agent.

These tests run against the deployed Cloud Run instance and verify
actual image generation functionality using real API calls.
"""

import base64
import os
from uuid import uuid4

import httpx
import pytest

CLOUD_RUN_URL = os.environ.get(
    'CREWAI_AGENT_URL',
    'https://a2a-demo-crewai-464922725547.us-central1.run.app',
)


@pytest.fixture
def http_client():
    """Create an HTTP client for testing."""
    return httpx.Client(timeout=120.0)


class TestAgentCard:
    """Tests for agent card endpoint."""

    def test_agent_card_returns_valid_json(self, http_client: httpx.Client):
        """Verify the agent card endpoint returns valid JSON with required fields."""
        response = http_client.get(f'{CLOUD_RUN_URL}/.well-known/agent.json')

        assert response.status_code == 200
        card = response.json()

        assert 'name' in card
        assert 'description' in card
        assert 'url' in card
        assert 'version' in card
        assert 'capabilities' in card

    def test_agent_card_has_correct_name(self, http_client: httpx.Client):
        """Verify the agent card has the expected name."""
        response = http_client.get(f'{CLOUD_RUN_URL}/.well-known/agent.json')
        card = response.json()

        assert (
            'image' in card['name'].lower() or 'crewai' in card['name'].lower()
        )

    def test_agent_card_declares_supported_content_types(
        self, http_client: httpx.Client
    ):
        """Verify the agent declares supported content types including image/png."""
        response = http_client.get(f'{CLOUD_RUN_URL}/.well-known/agent.json')
        card = response.json()

        if 'defaultInputModes' in card:
            input_modes = card['defaultInputModes']
            assert any('text' in mode.lower() for mode in input_modes)

        if 'defaultOutputModes' in card:
            output_modes = card['defaultOutputModes']
            assert any(
                'image' in mode.lower() or 'file' in mode.lower()
                for mode in output_modes
            )


class TestImageGeneration:
    """Tests for image generation functionality."""

    def test_generate_simple_image(self, http_client: httpx.Client):
        """Test generating a simple image returns valid artifact."""
        request_payload = {
            'jsonrpc': '2.0',
            'method': 'message/send',
            'params': {
                'message': {
                    'messageId': f'test-{uuid4().hex[:8]}',
                    'role': 'user',
                    'parts': [
                        {
                            'type': 'text',
                            'text': 'Generate an image of a blue circle',
                        }
                    ],
                }
            },
            'id': 1,
        }

        response = http_client.post(
            CLOUD_RUN_URL,
            json=request_payload,
            headers={'Content-Type': 'application/json'},
        )

        assert response.status_code == 200
        result = response.json()

        assert 'error' not in result, (
            f'Agent returned error: {result.get("error")}'
        )
        assert 'result' in result

        task_result = result['result']
        assert 'artifacts' in task_result
        assert len(task_result['artifacts']) > 0

    def test_generated_image_has_valid_base64_data(
        self, http_client: httpx.Client
    ):
        """Test that generated image contains valid base64-encoded PNG data."""
        request_payload = {
            'jsonrpc': '2.0',
            'method': 'message/send',
            'params': {
                'message': {
                    'messageId': f'test-{uuid4().hex[:8]}',
                    'role': 'user',
                    'parts': [
                        {
                            'type': 'text',
                            'text': 'Generate an image of a red square',
                        }
                    ],
                }
            },
            'id': 2,
        }

        response = http_client.post(
            CLOUD_RUN_URL,
            json=request_payload,
            headers={'Content-Type': 'application/json'},
        )

        result = response.json()
        assert 'result' in result, f'No result in response: {result}'

        artifacts = result['result']['artifacts']
        assert len(artifacts) > 0, 'No artifacts returned'

        artifact = artifacts[0]
        assert 'parts' in artifact
        assert len(artifact['parts']) > 0

        image_part = artifact['parts'][0]
        assert 'file' in image_part

        file_data = image_part['file']
        assert 'bytes' in file_data

        image_bytes = file_data['bytes']
        decoded = base64.b64decode(image_bytes)
        assert decoded[:8] == b'\x89PNG\r\n\x1a\n', 'Image is not a valid PNG'

    def test_generate_image_with_detailed_prompt(
        self, http_client: httpx.Client
    ):
        """Test generating image with a detailed prompt."""
        request_payload = {
            'jsonrpc': '2.0',
            'method': 'message/send',
            'params': {
                'message': {
                    'messageId': f'test-{uuid4().hex[:8]}',
                    'role': 'user',
                    'parts': [
                        {
                            'type': 'text',
                            'text': 'Generate an image of a sunset over the ocean with orange and purple colors in the sky',
                        }
                    ],
                }
            },
            'id': 3,
        }

        response = http_client.post(
            CLOUD_RUN_URL,
            json=request_payload,
            headers={'Content-Type': 'application/json'},
        )

        assert response.status_code == 200
        result = response.json()

        assert 'error' not in result, (
            f'Agent returned error: {result.get("error")}'
        )
        assert 'result' in result
        assert 'artifacts' in result['result']
        assert len(result['result']['artifacts']) > 0


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_method_returns_error(self, http_client: httpx.Client):
        """Test that invalid JSON-RPC method returns proper error."""
        request_payload = {
            'jsonrpc': '2.0',
            'method': 'invalid/method',
            'params': {},
            'id': 1,
        }

        response = http_client.post(
            CLOUD_RUN_URL,
            json=request_payload,
            headers={'Content-Type': 'application/json'},
        )

        assert response.status_code == 200
        result = response.json()

        assert 'error' in result
        assert result['error']['code'] == -32601

    def test_missing_message_returns_error(self, http_client: httpx.Client):
        """Test that missing message in params returns validation error."""
        request_payload = {
            'jsonrpc': '2.0',
            'method': 'message/send',
            'params': {},
            'id': 1,
        }

        response = http_client.post(
            CLOUD_RUN_URL,
            json=request_payload,
            headers={'Content-Type': 'application/json'},
        )

        assert response.status_code == 200
        result = response.json()

        assert 'error' in result


class TestA2AProtocolCompliance:
    """Tests for A2A protocol compliance."""

    def test_response_has_jsonrpc_version(self, http_client: httpx.Client):
        """Test that response includes JSON-RPC version."""
        request_payload = {
            'jsonrpc': '2.0',
            'method': 'message/send',
            'params': {
                'message': {
                    'messageId': f'test-{uuid4().hex[:8]}',
                    'role': 'user',
                    'parts': [
                        {'type': 'text', 'text': 'Generate a simple dot'}
                    ],
                }
            },
            'id': 99,
        }

        response = http_client.post(
            CLOUD_RUN_URL,
            json=request_payload,
            headers={'Content-Type': 'application/json'},
        )

        result = response.json()
        assert result.get('jsonrpc') == '2.0'

    def test_response_echoes_request_id(self, http_client: httpx.Client):
        """Test that response echoes the request ID."""
        test_id = 12345

        request_payload = {
            'jsonrpc': '2.0',
            'method': 'message/send',
            'params': {
                'message': {
                    'messageId': f'test-{uuid4().hex[:8]}',
                    'role': 'user',
                    'parts': [
                        {'type': 'text', 'text': 'Generate a tiny image'}
                    ],
                }
            },
            'id': test_id,
        }

        response = http_client.post(
            CLOUD_RUN_URL,
            json=request_payload,
            headers={'Content-Type': 'application/json'},
        )

        result = response.json()
        assert result.get('id') == test_id

    def test_artifact_has_required_fields(self, http_client: httpx.Client):
        """Test that artifacts have all required A2A fields."""
        request_payload = {
            'jsonrpc': '2.0',
            'method': 'message/send',
            'params': {
                'message': {
                    'messageId': f'test-{uuid4().hex[:8]}',
                    'role': 'user',
                    'parts': [
                        {'type': 'text', 'text': 'Generate a green triangle'}
                    ],
                }
            },
            'id': 1,
        }

        response = http_client.post(
            CLOUD_RUN_URL,
            json=request_payload,
            headers={'Content-Type': 'application/json'},
        )

        result = response.json()

        if 'result' in result and 'artifacts' in result['result']:
            for artifact in result['result']['artifacts']:
                assert 'artifactId' in artifact
                assert 'parts' in artifact


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
