import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from agent_executor import (
    WeatherReportingPoetExecutor,  # type: ignore[import-untyped]
)


if __name__ == '__main__':
    skill = AgentSkill(
        id='weather_reporting_poet',
        name='Weather Reporting Poet',
        description='Poet for latest weather updates',
        tags=['poet', 'weather'],
        examples=['How is the weather in Warsaw, Poland', 'How is the weather in Hyderabad, India'],
    )

    # This will be the public-facing agent card
    public_agent_card = AgentCard(
        name='Weather Reporting Poet',
        url='http://localhost:9999/',
        description='Weather reporting Poet',
        # icon_url='http://localhost:9999/',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(
            streaming=True, extended_agent_card=True
        ),
        supported_interfaces=[
            AgentInterface(
                protocol_binding='JSONRPC',
                url='http://localhost:9999',
                transport='HTTP+JSON'
            )
        ],
        skills=[skill],  # Only the basic skill for the public card
    )


    request_handler = DefaultRequestHandler(
        agent_executor=WeatherReportingPoetExecutor(),
        task_store=InMemoryTaskStore(), # Storage for User Tasks
    )

    server = A2AStarletteApplication(
        agent_card=public_agent_card,
        http_handler=request_handler,
    )

    uvicorn.run(server.build(), host='127.0.0.1', port=9999)
