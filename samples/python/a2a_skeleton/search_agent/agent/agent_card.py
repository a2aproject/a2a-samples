from a2a.types import AgentSkill, AgentCard, AgentCapabilities

def build_agent_card(host:str, port:int)->AgentCard:
    return AgentCard(
        name="Search Agent",
        description="구글 검색 결과를 제공하는 에이전트입니다.",
        url=f"http://{host}:{port}/",
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id='search_agent',
                name='Search Agent',
                description='구글 검색 결과를 제공하는 에이전트입니다.',
                tags=['search'],
            )
        ],
    )