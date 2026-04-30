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

import asyncio

from collections.abc import AsyncIterable

from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types


class WeatherReportingPoet:
    """An agent that reports weather updates in a haiku or poem format."""

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self) -> None:
        """Initializes the WeatherReportingPoet with necessary ADK services."""
        self._agent = LlmAgent(
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
        self._user_id = 'weather_reporting_poet'
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    async def run(self, query: str, session_id: str) -> str:
        """Runs the agent synchronously with the given query."""
        response = await self._runner.run_debug(
            user_id=self._user_id,
            session_id=session_id,
            user_messages=query,
            quiet=True,
        )
        return ''.join(
            part.text
            for event in response
            for part in event.content.parts
            if part.text
        )

    async def stream(
        self, query: str, session_id: str
    ) -> AsyncIterable[tuple[bool, str]]:
        """Streams the agent's response to the query."""
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        ) or await self._runner.session_service.create_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            state={},
            session_id=session_id,
        )

        content = types.Content(
            role='user', parts=[types.Part.from_text(text=query)]
        )
        async for event in self._runner.run_async(
            user_id=self._user_id, session_id=session.id, new_message=content
        ):
            yield (
                event.is_final_response(),
                '\n'.join(p.text for p in event.content.parts if p.text)
                if event.is_final_response()
                else 'working...',
            )


if __name__ == '__main__':
    poet = WeatherReportingPoet()
    print('################################')
    print('#### Weather Reporting Poet ####')
    print('################################')
    print('To exit use `exit` or `quit`.\n---')
    query = 'How is the weather in Warsaw, Poland today?'
    print(f'user> {query}')
    while query not in ['exit', 'quit']:
        if query:
            response = asyncio.run(poet.run(query, 'mock_session'))
            print(f'model> {response}\n---')
        query = input('user> ').strip()
