import logging
import json
import re
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk import Runner
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.genai import types
from a2a.types import AgentCard

from agent.agent_connect import AgentConnector
from prompts.prompt import SYSTEM_INSTRUCTION

logger = logging.getLogger(__name__)
MAX_RETRY = 3

def extract_json_from_llm_output(text):
    """
    LLM 응답에서 ```json ... ``` 코드블록이 감싸져 있으면 내부만 추출해서 반환.
    코드블록이 없으면 그대로 반환.
    """
    match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text)
    if match:
        return match.group(1)
    return text

class HostAgent:
    """
    🤖 Gemini LLM을 사용하여 들어오는 사용자 쿼리를 라우팅하고,
    도구를 통해 발견된 하위 A2A 에이전트들을 호출합니다.
    """

    def __init__(self, agent_cards: list[AgentCard]):
        logger.info(f"agent_cards: {agent_cards}")
        self.connectors = {
            card.name: AgentConnector(card.name, card.url)
            for card in agent_cards
        }
        self.agent = self._build_agent()
        self.runner = Runner(
            app_name="host_agent",
            agent=self.agent,
            session_service=InMemorySessionService()
        )

    def _build_agent(self) -> LlmAgent:
        agent = LlmAgent(
            model='gemini-2.0-flash',
            name='host_agent',
            description='외부 에이전트로 라우팅하는 멀티에이전트 조정자',
            instruction=SYSTEM_INSTRUCTION,
            tools=[self._list_agents], 
        )
        return agent

    def _list_agents(self) -> list[str]:
        return list(self.connectors.keys())


    async def invoke(self, query, session_id, task_id, user_id=None):
        for retry in range(MAX_RETRY):
            try :
                session = await self.runner.session_service.get_session(
                    app_name="host_agent",
                    user_id=user_id,
                    session_id=session_id
                )
            
                if session is None:
                    session = await self.runner.session_service.create_session(
                        app_name="host_agent",
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
                        max_llm_calls=200
                    )
                ):
                    event_dict = event.dict()
                    text = event_dict['content']['parts'][0]['text']
                    json_str = extract_json_from_llm_output(text)

                    data = json.loads(json_str)
                    agent = data["agent"]
                    query = data["query"]
                    async for chunk in self.connectors[agent].send_task(query, session_id, task_id, user_id):
                        yield chunk
                return
            except Exception as e :
                raise
        yield {"error": "LLM이 올바른 포맷/에이전트 이름을 반환하지 못했습니다."}

