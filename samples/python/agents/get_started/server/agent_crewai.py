import asyncio
import random

from collections.abc import AsyncIterable

from crewai import LLM, Agent, Crew, Task
from crewai.process import Process
from crewai.tools import tool


@tool('get_weather')
def get_weather(city: str) -> str:
    """Get weather for a given city."""
    messages = [
        f"It's always sunny in {city}! Temperature is 25°C, wind is 10 km/h NW, and there's 0% precipitation.",
        f'A cozy, rainy day in {city}. Temperature sits at 15°C, gentle breeze of 5 km/h from East, with 80% precipitation.',
        f'Brisk and windy in {city}! Temperature is 10°C, fierce winds at 45 km/h North, and a 20% chance of precipitation.',
        f'Surprisingly snowy in {city}! Temperature dropped to -2°C, calm winds at 3 km/h, and 100% fluffy snow precipitation.',
        f'A perfect autumn afternoon in {city}. Temperature is 18°C, mild wind at 12 km/h SW, with 5% precipitation.',
    ]
    return random.choice(messages)  # noqa: S311


class WeatherReportingPoet:
    """An agent that reports weather updates in a haiku or poem format using CrewAI."""

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self) -> None:
        self._user_id = 'weather_reporting_poet'
        self._model = LLM(model='gemini/gemini-2.0-flash')

        self._agent = Agent(
            role='Weather Reporting Agent',
            goal='Report on temperature and weather for the next 4-6 hours in simple and easy to sing Poems (4 lines) or Haikus (3 lines).',
            backstory='You are a poetic Weather Reporting Agent who loves answering in brief poems or haikus. You use the get_weather tool to find information.',
            instruction="""
            You are a Weather Reporting Agent.
            Your report should include details on temperature and weather for next 4-6 hours.
            You often respond in 1 or 2 a Poems (4 lines each) or Haikus (3 lines each).
            Generated Haiku's or Poems should be simple and easy to sing.
            Use get_weather tool to find information as and when required.
            """,
            verbose=False,
            allow_delegation=False,
            tools=[get_weather],
            llm=self._model,
        )

        self._task = Task(
            description='Provide the poetic weather report for the following request: {query}',
            expected_output='A poetic weather report consisting of simple, easy-to-sing poems or haikus containing the requested temperature and weather for the next 4-6 hours.',
            agent=self._agent,
        )

        self._crew = Crew(
            agents=[self._agent],
            tasks=[self._task],
            process=Process.sequential,
            verbose=False,
        )

    async def run(self, query: str, session_id: str) -> str:
        """Runs the agent synchronously with the given query."""
        result = await asyncio.to_thread(self._crew.kickoff, {'query': query})
        return str(result)

    async def stream(
        self, query: str, session_id: str
    ) -> AsyncIterable[tuple[bool, str]]:
        """Streams the agent's response."""
        yield (False, 'working...')
        response = await self.run(query, session_id)
        yield (True, response)


async def main() -> None:
    """Runs test queries for the CrewAI weather poet."""
    poet = WeatherReportingPoet()
    print('################################')
    print('#### CrewAI Weather Poet    ####')
    print('################################')
    print('To exit use `exit` or `quit`.\n---')

    query = 'How is the weather in Warsaw, Poland today?'
    print(f'user> {query}')
    response = await poet.run(query, 'mock_session')
    print(f'model> {response}\n---')

    query = 'How is the weather in Berlin, Germany today?'
    print(f'user> {query}')
    response = await poet.run(query, 'mock_session')
    print(f'model> {response}\n---')

    query = 'How is the weather in Paris, France today?'
    print(f'user> {query}')
    response = await poet.run(query, 'mock_session')
    print(f'model> {response}\n---')

    query = 'How is the weather in Madrid, Spain today?'
    print(f'user> {query}')
    response = await poet.run(query, 'mock_session')
    print(f'model> {response}\n---')


if __name__ == '__main__':
    asyncio.run(main())

