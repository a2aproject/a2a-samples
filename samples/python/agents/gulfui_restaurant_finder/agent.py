import os

from collections.abc import AsyncIterable
from typing import Any

from google.adk.agents.llm_agent import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


class RestaurantAgent:
    """An agent that finds restaurants based on user criteria."""

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self, base_url: str):
        # Pass base_url to the _build_agent method
        self._agent = self._build_agent(base_url=base_url)
        self._user_id = 'remote_agent'
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    def get_processing_message(self) -> str:
        return 'Finding restaurants that match your criteria...'

    def _build_agent(self, base_url: str) -> LlmAgent:
        """Builds the LLM agent for the restaurant agent."""
        LITELLM_MODEL = os.getenv(
            'LITELLM_MODEL', 'gemini/gemini-2.0-flash-001'
        )
        return LlmAgent(
            model=LiteLlm(model=LITELLM_MODEL),
            name='restaurant_agent',
            description=(
                'This agent finds restaurants based on user criteria like cuisine,'
                ' location, or rating.'
            ),
            instruction=f"""
    You are a helpful restaurant finding assistant.
    When a user provides you with criteria (like "top 10 chinese restaurants in the US",
    "best pizza places near downtown", or "cheap eats in Paris"),
    you must find and return a list of restaurants that match.

    For each restaurant in the list, you MUST select a relevant placeholder image
    from the following available list. You must return the path formatted as a
    full, absolute URL by prepending the base URL: {base_url}

    Example Format: {base_url}/static/FILENAME

    Available image paths:
    - /static/beefbroccoli.jpeg
    - /static/sweetsourpork.jpeg
    - /static/springrolls.jpeg
    - /static/mapotofu.jpeg
    - /static/kungpao.jpeg
    - /static/shrimpchowmein.jpeg
    - /static/vegfriedrice.jpeg

    You must include this absolute URL in a field named `imageUrl`.
    If no image seems relevant, you can pick one at random from the list.

    Present the answer clearly to the user, following the UI format instructions.
    """,
            tools=[],
        )

    async def stream(self, query, session_id) -> AsyncIterable[dict[str, Any]]:
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
                response = ''
                if (
                    event.content
                    and event.content.parts
                    and event.content.parts[0].text
                ):
                    response = '\n'.join(
                        [p.text for p in event.content.parts if p.text]
                    )

                yield {
                    'is_task_complete': True,
                    'content': response,
                }
            else:
                yield {
                    'is_task_complete': False,
                    'updates': self.get_processing_message(),
                }
