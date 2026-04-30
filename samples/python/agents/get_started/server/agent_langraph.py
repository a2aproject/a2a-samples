import asyncio
import random

from collections.abc import AsyncIterable

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent


@tool
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
    """An agent that reports weather updates in a haiku or poem format using LangGraph."""

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    SYSTEM_INSTRUCTION = """
    You are a Weather Reporting Agent.
    Your report should include details on temperature and weather for next 4-6 hours.
    You often respond in 1 or 2 a Poems (4 lines each) or Haikus (3 lines each).
    Generated Haiku's or Poems should be simple and easy to sing.
    Use the get_weather tool to find information as and when required.
    """

    def __init__(self) -> None:
        self._user_id = 'weather_reporting_poet'
        self._model = ChatGoogleGenerativeAI(model='gemini-2.5-flash-lite')
        self._tools = [get_weather]
        self._memory = MemorySaver()

        self._graph = create_react_agent(
            self._model,
            tools=self._tools,
            checkpointer=self._memory,
            prompt=self.SYSTEM_INSTRUCTION,
        )

    async def run(self, query: str, session_id: str) -> str:
        """Runs the agent synchronously with the given query."""
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': session_id}}
        result = await self._graph.ainvoke(inputs, config)
        return str(result['messages'][-1].content)

    async def stream(
        self, query: str, session_id: str
    ) -> AsyncIterable[tuple[bool, str]]:
        """Streams the agent's response."""
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': session_id}}

        async for event in self._graph.astream(
            inputs, config, stream_mode='values'
        ):
            if event.get('messages'):
                latest_message = event['messages'][-1]
                if (
                    isinstance(latest_message, AIMessage)
                    and latest_message.tool_calls
                ):
                    yield (False, 'Looking up weather information...')
                elif isinstance(latest_message, ToolMessage):
                    yield (False, 'Analyzing weather data...')
                elif (
                    isinstance(latest_message, AIMessage)
                    and latest_message.content
                ):
                    yield (False, 'working...')

        result = await self.run(query, session_id)
        yield (True, result)


if __name__ == '__main__':
    poet = WeatherReportingPoet()
    print('################################')
    print('#### LangGraph Weather Poet ####')
    print('################################')
    print('To exit use `exit` or `quit`.\n---')
    query = 'How is the weather in Warsaw, Poland today?'
    print(f'user> {query}')
    while query not in ['exit', 'quit']:
        if query:
            response = asyncio.run(poet.run(query, 'mock_session'))
            print(f'model> {response}\n---')
        query = input('user> ').strip()
