from collections.abc import AsyncIterable

from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.tools import google_search



def create_agent() -> LlmAgent:
    return LlmAgent(
        model='gemini-2.5-flash',
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
    """An agent that report weather updates in a haiku or poem format."""

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self) -> None:
        self._agent = create_agent()
        self._user_id = 'weather_reporting_poet'
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    async def run(self, query: str, session_id: str) -> str|list[str]:
        """Run the agent with the given query."""
        response = await self._runner.run_debug(
            user_id=self._user_id,
            session_id=session_id,
            user_messages=query,
        )
        return response

    async def stream(
        self, query: str, session_id: str
    ) -> AsyncIterable[tuple[bool, str]]:
        """Stream the response to the query."""
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
    asyncio.run(poet.run("How is the weather in Warsaw, Poland today?", "mock_session"))
    # Example output:
    #     (.venv) $ python run.py
    #
    #      ### Created new session: debug_session_id
    #
    #     User > How is the weather in Warsaw, Poland today?
    #     haiku_generator > Warsaw skies today,
    #     Partly sunny, then light rain,
    #     Cool breeze, eight degrees.
