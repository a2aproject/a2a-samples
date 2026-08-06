from a2a.types import AgentCard, AgentCapabilities, AgentSkill

def build_agent_card(host:str, port:int) -> AgentCard:
    return AgentCard(
        name="Host Agent",
        description="발견된 하위 에이전트에게 작업을 위임합니다.",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=True),
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        skills=[
            AgentSkill(
                id="host_agent",
                name="host_agent",
                description="사용자 요청을 의도에따라 적절한 하위 에이전트로 라우팅 합니다.",
                tags=["host_agent"],
            )
        ]
    )