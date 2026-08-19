# ruff: noqa: N999 - the sample lives in a hyphenated directory
import logging
import os

import click
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from dotenv import load_dotenv
from openai_agent import create_agent  # type: ignore[import-not-found]
from openai_agent_executor import (  # type: ignore[import-untyped]
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    ORCAROUTER_BASE_URL,
    ORCAROUTER_MODEL,
    OpenAIAgentExecutor,
    OpenAICompatibleProvider,
)
from starlette.applications import Starlette


load_dotenv()

logging.basicConfig()


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10007)
def main(host: str, port: int) -> None:
    """Run the A2A GitHub agent server."""
    # Pick the active provider. OrcaRouter is used when its key is set,
    # otherwise the sample falls back to OpenRouter.
    api_key = os.getenv('ORCAROUTER_API_KEY') or os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        raise ValueError('ORCAROUTER_API_KEY or OPENROUTER_API_KEY environment variable not set')
    base_url = ORCAROUTER_BASE_URL if os.getenv('ORCAROUTER_API_KEY') else OPENROUTER_BASE_URL
    model = ORCAROUTER_MODEL if os.getenv('ORCAROUTER_API_KEY') else OPENROUTER_MODEL
    provider = OpenAICompatibleProvider(
        api_key=api_key,
        base_url=base_url,
        model=model,
        default_headers={
            'HTTP-Referer': 'http://localhost:10007',
            'X-Title': 'GitHub Agent',
        },
    )

    skill = AgentSkill(
        id='github_repositories',
        name='GitHub Repositories',
        description='Query GitHub repositories, recent updates, commits, and project activity',
        tags=['github', 'repositories', 'commits'],
        examples=[
            'Show my recent repository updates',
            'What are the latest commits in my project?',
            'Search for popular Python repositories with recent activity',
        ],
    )

    # AgentCard for OpenAI-based agent
    agent_card = AgentCard(
        name='GitHub Agent',
        description='An agent that can query GitHub repositories and recent project updates',
        url=f'http://{host}:{port}/',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )

    # Create OpenAI agent
    agent_data = create_agent()

    agent_executor = OpenAIAgentExecutor(
        card=agent_card,
        tools=agent_data['tools'],
        provider=provider,
        system_prompt=agent_data['system_prompt'],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, task_store=InMemoryTaskStore()
    )

    a2a_app = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)
    routes = a2a_app.routes()

    app = Starlette(routes=routes)

    uvicorn.run(app, host=host, port=port)


if __name__ == '__main__':
    main()
