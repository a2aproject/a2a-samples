"""
Sample agent that demonstrates iframe embedded UI component support in A2A protocol.

This agent shows how to embed various types of UI components like charts, dashboards,
and forms using iframes as referenced in the A2A protocol specification.
"""

import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from agent_executor import IframeDemoAgentExecutor


if __name__ == '__main__':
    # Define agent skills
    skills = [
        AgentSkill(
            id='show_chart',
            name='Show Chart',
            description='Display a sample chart in an embedded iframe',
            tags=['iframe', 'chart', 'visualization'],
            examples=['show me a chart', 'display a chart', 'chart visualization']
        ),
        AgentSkill(
            id='show_dashboard',
            name='Show Dashboard',
            description='Display a sample dashboard in an embedded iframe',
            tags=['iframe', 'dashboard', 'analytics'],
            examples=['show me a dashboard', 'display dashboard', 'analytics dashboard']
        ),
        AgentSkill(
            id='show_form',
            name='Show Form',
            description='Display a sample form in an embedded iframe',
            tags=['iframe', 'form', 'input'],
            examples=['show me a form', 'display a form', 'embed form']
        ),
        AgentSkill(
            id='embed_url',
            name='Embed URL',
            description='Embed any URL as an iframe component',
            tags=['iframe', 'url', 'embed'],
            examples=['embed https://example.com', 'show https://example.com', 'display url']
        ),
    ]

    # Create agent card
    agent_card = AgentCard(
        name='Iframe Demo Agent',
        description=(
            'Demonstrates iframe embedded UI component support in A2A protocol. '
            'Can display charts, dashboards, forms, and other web content in conversations.'
        ),
        url='http://localhost:10002/',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text', 'iframe'],
        capabilities=AgentCapabilities(streaming=True),
        skills=skills,
    )

    # Create request handler
    request_handler = DefaultRequestHandler(
        agent_executor=IframeDemoAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    
    # Create A2A server app
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    
    # Run the server
    uvicorn.run(server.build(), host='0.0.0.0', port=10002)