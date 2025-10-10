from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk import Runner
from google.adk.tools.google_search_tool import google_search
from google.genai import types
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.run_config import RunConfig, StreamingMode
from a2a.types import AgentCard

from prompts.prompt import SYSTEM_INSTRUCTION

import uuid
import httpx
import json
import logging

logger = logging.getLogger(__name__)

class SearchAgent:

    def __init__(self):
        self.agent = self._build_agent()
        self.runner = Runner(
            app_name="search_agent",
            agent=self.agent,
            session_service=InMemorySessionService(),
        )
    
    def _build_agent(self)->LlmAgent:
        return LlmAgent(
            model='gemini-2.0-flash',
            name="search_agent",
            description="구글 검색 결과를 제공하는 에이전트입니다.",
            instruction=SYSTEM_INSTRUCTION,
            tools=[google_search],
        )

    async def invoke(self, query :str, session_id:str, task_id:str, user_id:str)-> str:
        try :
            session = await self.runner.session_service.get_session(
                    app_name="search_agent",
                    user_id=user_id,
                    session_id=session_id
                )
            
            if session is None:
                session = await self.runner.session_service.create_session(
                    app_name="search_agent",
                    user_id=user_id,
                    session_id=session_id,
                    state={}
                )
            invocation_context = InvocationContext(
                session_service=self.runner.session_service,
                invocation_id=task_id,
                agent=self.agent,
                session=session
            )

            content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=query)]
            )

            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=content,
                run_config=RunConfig(
                    streaming_mode=StreamingMode.SSE,
                    max_llm_calls=200
                )
            ):
                yield event
            return
        except Exception as e :
            logger.error(f"[INVOKE] 예외 발생: {e}", exc_info=True)
            raise
