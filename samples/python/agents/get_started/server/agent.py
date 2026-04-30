# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module defining the Weather Reporting Poet agent using Google ADK."""

from collections.abc import AsyncIterable

from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types


def create_weather_poet_agent() -> LlmAgent:
    """Creates and configures the core LLM agent for weather reporting.

    Returns:
        LlmAgent: An instance of the configured agent.
    """
    return LlmAgent(
        model='gemini-2.5-flash-lite',
        name='poet_weather_report',
        instruction="""
        You are a Weather Reporting Agent.
        Your report should include details on temperature and weather for next 4-6 hours.
        You often respond in 1 or 2 a Poems (4 lines each) or Haikus (3 lines each).
        Generated Haiku's or Poems should be simple and easy to sing.
        Use Google search tool to find factual information as and when required.
        """,
        description='Weather Reporting Poet',
        tools=[google_search],
    )


class WeatherReportingPoet:
    """An agent that reports weather updates in a haiku or poem format.

    This class wraps the Google ADK Runner to provide both synchronous
    and streaming interfaces for generating poetic weather reports.
    """

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self) -> None:
        """Initializes the WeatherReportingPoet with necessary ADK services."""
        self._agent = create_weather_poet_agent()
        self._user_id = 'weather_reporting_poet'
        # Initialize the ADK Runner with in-memory services for state management
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    async def run(self, query: str, session_id: str) -> str | list[str]:
        """Runs the agent synchronously with the given query.

        Args:
            query: The user's weather query.
            session_id: Unique identifier for the conversation session.

        Returns:
            A string containing the poetic weather report.
        """
        # Execute the agent using the debug runner
        response = await self._runner.run_debug(
            user_id=self._user_id,
            session_id=session_id,
            user_messages=query,
            quiet=True,
        )
        text_response = []
        # Accumulate text parts from the response events
        for event in response:
            for part in event.content.parts:
                text_response.extend(part.text)
        return ''.join(text_response)

    async def stream(
        self, query: str, session_id: str
    ) -> AsyncIterable[tuple[bool, str]]:
        """Streams the agent's response to the query.

        Args:
            query: The user's weather query.
            session_id: Unique identifier for the conversation session.

        Yields:
            A tuple where the first element is a boolean (True if final)
            and the second is the response text chunk.
        """
        # Retrieve or create the session
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        content = types.Content(
            role='user', parts=[types.Part.from_text(text=query)]
        )
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )

        # Stream the response using the async runner
        async for event in self._runner.run_async(
            user_id=self._user_id, session_id=session.id, new_message=content
        ):
            if event.is_final_response():
                yield (
                    True,
                    '\n'.join([p.text for p in event.content.parts if p.text]),
                )
            else:
                yield (False, 'working...')


if __name__ == '__main__':
    import asyncio

    poet = WeatherReportingPoet()
    print('################################')
    print('#### Weather Reporting Poet ####')
    print('################################')
    print('To exit use `exit` or `quit`.')
    print('---')
    query = 'How is the weather in Warsaw, Poland today?'
    print(f'user> {query}')
    while query not in ['exit', 'quit']:
        if query:
            response = asyncio.run(poet.run(query, 'mock_session'))
            print(f'model> {response}')
            print('---')
        query = input('user> ').strip()

