import json
import os
from collections.abc import AsyncIterable
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel
from autogen import AssistantAgent, UserProxyAgent

load_dotenv()


class ResponseFormat(BaseModel):
    """Respond to the user in this format."""

    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str


class CurrencyAgent:
    """A currency conversion agent using AutoGen."""

    SYSTEM_INSTRUCTION = (
        'You are a specialized assistant for currency conversions. '
        "Your sole purpose is to use the 'get_exchange_rate' tool to answer questions about currency exchange rates. "
        'If the user asks about anything other than currency conversion or exchange rates, '
        'politely state that you cannot help with that topic and can only assist with currency-related queries. '
        'Set response status to input_required if the user needs to provide more information. '
        'Set response status to error if there is an error while processing the request. '
        'Set response status to completed if the request is complete.'
    )

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self):
        self.config_list = self._get_config()
        self.assistant = self._create_assistant()
        self.user_proxy = self._create_user_proxy()
        self.tools = [self.get_exchange_rate]
        self.session_data: dict[str, Any] = {}

    def _get_config(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError('OPENAI_API_KEY environment variable not set')
        return [{'model': 'gpt-4', 'api_key': api_key}]

    def _create_assistant(self):
        return AssistantAgent(
            name='currency_assistant',
            system_message=self.SYSTEM_INSTRUCTION,
            llm_config={'config_list': self.config_list},
        )

    def _create_user_proxy(self):
        return UserProxyAgent(
            name='user_proxy',
            human_input_mode='NEVER',
            function_map={'get_exchange_rate': self.get_exchange_rate},
        )

    def get_exchange_rate(
        self,
        currency_from: str = 'USD',
        currency_to: str = 'EUR',
        currency_date: str = 'latest',
    ) -> dict[str, Any]:
        try:
            response = httpx.get(
                f'https://api.frankfurter.app/{currency_date}',
                params={'from': currency_from, 'to': currency_to},
            )
            response.raise_for_status()
            data = response.json()
            if 'rates' not in data:
                return {'error': 'Invalid API response format.'}
            return data
        except httpx.HTTPError as e:
            return {'error': f'API request failed: {e}'}
        except ValueError:
            return {'error': 'Invalid JSON response from API.'}

    def _format_response(self, response: str) -> dict[str, Any]:
        try:
            response_lines = response.strip().split('\n')
            json_content = None
            for line in response_lines:
                if '{"status":' in line or '"status":' in line:
                    try:
                        start = line.find('{')
                        end = line.rfind('}') + 1
                        content = line[start:end]
                        parsed = json.loads(content)
                        if 'status' in parsed and 'message' in parsed:
                            status = parsed['status']
                            message = parsed['message']
                            return {
                                'is_task_complete': status == 'completed',
                                'require_user_input': status == 'input_required',
                                'content': message,
                            }
                    except json.JSONDecodeError:
                        continue
            if 'i need more information' in response.lower():
                return {'is_task_complete': False, 'require_user_input': True, 'content': response}
            return {'is_task_complete': True, 'require_user_input': False, 'content': response}
        except Exception as e:
            return {'is_task_complete': False, 'require_user_input': True,
                    'content': f'Error processing response: {e}\nOriginal response: {response}'}

    def invoke(self, query: str, sessionId: str) -> dict[str, Any]:
        if sessionId not in self.session_data:
            self.session_data[sessionId] = []
        self.assistant.reset()
        self.user_proxy.reset()
        self.user_proxy.initiate_chat(self.assistant, message=query, clear_history=False)
        chat_history = self.assistant.chat_messages[self.user_proxy.name]
        response = chat_history[-1]['content'] if chat_history else "I couldn't process your request."
        self.session_data[sessionId].append({'role': 'user', 'content': query})
        self.session_data[sessionId].append({'role': 'assistant', 'content': response})
        return self._format_response(response)

    async def stream(self, query: str, sessionId: str) -> AsyncIterable[dict[str, Any]]:
        if sessionId not in self.session_data:
            self.session_data[sessionId] = []
        self.session_data[sessionId].append({'role': 'user', 'content': query})
        self.assistant.reset()
        self.user_proxy.reset()
        yield {'is_task_complete': False, 'require_user_input': False, 'content': 'Looking up the exchange rates...'}
        self.user_proxy.initiate_chat(self.assistant, message=query, clear_history=False)
        yield {'is_task_complete': False, 'require_user_input': False, 'content': 'Processing the exchange rates..'}
        chat_history = self.assistant.chat_messages[self.user_proxy.name]
        response = chat_history[-1]['content'] if chat_history else "I couldn't process your request."
        self.session_data[sessionId].append({'role': 'assistant', 'content': response})
        yield self._format_response(response)