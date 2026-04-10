import click
import uvicorn

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    GetTaskRequest,
    Message,
    SendMessageRequest,
    Task,
)
from starlette.applications import Starlette

from no_llm_framework.server.agent_executor import HelloWorldAgentExecutor


class A2ARequestHandler(DefaultRequestHandler):
    """A2A Request Handler for the A2A Repo Agent."""

    def __init__(
        self,
        agent_executor: AgentExecutor,
        task_store: InMemoryTaskStore,
        agent_card: AgentCard,
    ):
        super().__init__(agent_executor, task_store, agent_card)

    async def on_get_task(
        self, request: GetTaskRequest, context: RequestContext
    ) -> Task:
        """Get task."""
        return await super().on_get_task(request, context)

    async def on_message_send(
        self, request: SendMessageRequest, context: RequestContext
    ) -> Message | Task:
        """Handle message send."""
        return await super().on_message_send(request, context)


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=9999)
def main(host: str, port: int) -> None:
    """Start the A2A Repo Agent server.

    This function initializes the A2A Repo Agent server with the specified host and port.
    It creates an agent card with the agent's name, description, version, and capabilities.

    Args:
        host (str): The host address to run the server on.
        port (int): The port number to run the server on.
    """
    skill = AgentSkill(
        id='answer_detail_about_A2A_repo',
        name='Answer any information about A2A repo',
        description='The agent will look up the information about A2A repo and answer the question.',
        tags=['A2A repo'],
        examples=['What is A2A repo?', 'What is Google A2A repo?'],
    )

    agent_card = AgentCard(
        name='A2A Protocol Agent',
        description='A2A Protocol knowledge agent who has information about A2A Protocol and can answer questions about it',
        supported_interfaces=[
            AgentInterface(
                protocol_binding='JSONRPC',
                url=f'http://{host}:{port}/',
            )
        ],
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(
            streaming=True,
        ),
        skills=[skill],
    )

    task_store = InMemoryTaskStore()
    request_handler = A2ARequestHandler(
        agent_executor=HelloWorldAgentExecutor(),
        task_store=task_store,
        agent_card=agent_card,
    )

    routes = []
    routes.extend(create_agent_card_routes(agent_card))
    routes.extend(create_jsonrpc_routes(request_handler, rpc_url='/'))

    app = Starlette(routes=routes)
    uvicorn.run(app, host=host, port=port)


if __name__ == '__main__':
    main()
