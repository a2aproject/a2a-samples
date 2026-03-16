"""Shared LLM configuration for the AG2 A2A sample."""

import os

from autogen import LLMConfig


def get_llm_config() -> LLMConfig:
    """Build LLM config from environment variables.

    Supports Gemini (default) and OpenAI.
    Set GOOGLE_API_KEY for Gemini or OPENAI_API_KEY for OpenAI.

    Returns:
        LLMConfig configured for the detected provider.

    Raises:
        ValueError: If neither GOOGLE_API_KEY nor OPENAI_API_KEY is set.
    """
    google_key = os.getenv('GOOGLE_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    if not google_key and not openai_key:
        msg = (
            'Set GOOGLE_API_KEY (for Gemini) or '
            'OPENAI_API_KEY (for OpenAI) in your environment.'
        )
        raise ValueError(msg)
    if google_key:
        return LLMConfig(
            {
                'api_type': 'google',
                # Change to 'gemini-2.5-flash' or another model as needed.
                'model': 'gemini-3-flash-preview',
                'api_key': google_key,
            }
        )
    return LLMConfig(
        {
            # Change to 'gpt-4o' or another model as needed.
            'model': 'gpt-4o-mini',
            'api_key': openai_key,
        }
    )
