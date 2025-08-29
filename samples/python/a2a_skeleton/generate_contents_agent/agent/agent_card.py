from a2a.types import AgentSkill, AgentCard, AgentCapabilities

def build_agent_card(host:str, port:int)->AgentCard:
    return AgentCard(
        name="Generate Contents Agent",
        description="콘텐츠를 생성하는 에이전트입니다.",
        url=f"http://{host}:{port}/",
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id='generate_contents_agent',
                name='Generate Contents Agent',
                description='콘텐츠를 생성하는 에이전트입니다.',
                tags=['generate_contents'],
            )
        ],
    )