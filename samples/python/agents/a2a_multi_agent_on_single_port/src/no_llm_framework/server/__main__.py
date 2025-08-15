import click
import uvicorn
from a2a.server.apps.jsonrpc import A2AStarletteApplication
from a2a.server.request_handlers.default_request_handler import (
    DefaultRequestHandler,
)
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard
)
from starlette.applications import Starlette
from starlette.routing import Route, Router
from starlette.requests import Request
from typing import Any, List
from a2a.server.request_handlers.jsonrpc_handler import JSONRPCHandler

from no_llm_framework.server.agent_executor import CoreAgentExecutor
from starlette.responses import JSONResponse


class DynamicContextBuilder:
    def __init__(self, original_builder, agent_index):
        self.original_builder = original_builder
        self.agent_index = agent_index

    async def build(self, request: Request):
        if self.original_builder and hasattr(self.original_builder, "build"):
            context = await self.original_builder.build(request)
        else:
            context = None

        if context:
            setattr(context, "agent_index", self.agent_index)
        return context


class DatabaseA2AStarletteApplication(A2AStarletteApplication):
    def __init__(self, http_handler: DefaultRequestHandler):
        temp_card = AgentCard(
            name="Temporary Agent",
            description="Initial agent card",
            url="http://localhost:9999/a2a/default",
            version="1.0.0",
            defaultInputModes=["text"],
            defaultOutputModes=["text"],
            capabilities=AgentCapabilities(
                inputModes=["text"], outputModes=["text"], streaming=True
            ),
            skills=[],
            examples=[],
        )

        self.task_store = InMemoryTaskStore()

        self.agent_card = temp_card
        self.http_handler = http_handler
        self.handler = JSONRPCHandler(
            agent_card=self.agent_card, request_handler=self.http_handler
        )

        self.agent_router = Router()

        self.agent_router.add_route(
            "/.well-known/agent.json", self._handle_dynamic_agent_card, methods=["GET"]
        )
        self.agent_router.add_route("/", self._handle_dynamic_request, methods=["POST"])

    def _get_agent_card_from_config(self, agent_index: str, request: Request) -> AgentCard:
        
        agent_data = {
            "name": "default",
            "description": "default",
            "version": "1.0.0",
            "examples": "What is A2A protocol?"
        }
        
        return AgentCard(
            name=agent_data["name"],
            description=agent_data["description"],
            url=f"http://{request.url.hostname}:{request.url.port}/a2a/{agent_index}",
            version=agent_data["version"],
            defaultInputModes=["text"],
            defaultOutputModes=["text"],
            capabilities=AgentCapabilities(
                inputModes=["text"],
                outputModes=["text"],
                streaming=True,
            ),
            skills=[],
            examples=agent_data["examples"] or [],
        )

    def routes(
        self,
        rpc_url: str = "/",
        extended_agent_card_url: str = "/agent/authenticatedExtendedCard",
        **kwargs,
    ) -> List[Route]:
        routes = [
            Route(rpc_url, self._handle_requests, methods=["POST"]),

            Route(
                "/a2a/{agent_index}/.well-known/agent.json",
                self._handle_dynamic_agent_card,
                methods=["GET"],
            ),

            Route("/a2a/{agent_index}", self._handle_dynamic_request, methods=["POST"]),
        ]

        if self.agent_card and self.agent_card.supportsAuthenticatedExtendedCard:
            routes.append(
                Route(
                    extended_agent_card_url,
                    self._handle_get_authenticated_extended_agent_card,
                    methods=["GET"],
                )
            )

        return routes

    async def _handle_dynamic_agent_card(self, request: Request) -> JSONResponse:

        agent_index = request.path_params["agent_index"]
        try:
            card = self._get_agent_card_from_config(agent_index, request)
            return JSONResponse(card.dict())
        except Exception as e:
            return JSONResponse(
                {"error": f"Agent not found: {str(e)}"}, status_code=404
            )

    async def _handle_dynamic_request(self, request: Request) -> JSONResponse:

        original_card = None
        original_context_builder = None

        try:
            agent_index = request.path_params.get("agent_index")
            self.task_store = InMemoryTaskStore()
            self.http_handler.agent_executor = CoreAgentExecutor(
                agent_index=agent_index
            )

            if not agent_index:
                return JSONResponse(
                    {"error": "Missing agent_index in path parameters"}, status_code=400
                )

            original_card = self.agent_card
            original_context_builder = getattr(self, "_context_builder", None)

            try:
                self.agent_card = self._get_agent_card_from_config(agent_index, request)
                self.handler.agent_card.name = self.agent_card.name
                self.handler.agent_card.description = self.agent_card.description
            except Exception as e:
                return JSONResponse(
                    {"error": f"Failed to get agent card: {str(e)}"}, status_code=404
                )

            self._context_builder = DynamicContextBuilder(
                original_context_builder, agent_index
            )

            response = await self._handle_requests(request)
            return response
        except Exception as e:
            import traceback

            traceback.print_exc()
            return JSONResponse(
                {
                    "error": "Internal server error",
                    "details": str(e),
                    "type": type(e).__name__,
                },
                status_code=500,
            )
        finally:

            if original_card is not None:
                self.agent_card = original_card
            if original_context_builder is not None:
                self._context_builder = original_context_builder

    def build(
        self,
        agent_card_url: str = "/.well-known/agent.json",
        rpc_url: str = "/",
        extended_agent_card_url: str = "/agent/authenticatedExtendedCard",
        **kwargs: Any,
    ) -> Starlette:
        app = Starlette(**kwargs)
        self.add_routes_to_app(
            app,
            agent_card_url=agent_card_url,
            rpc_url=rpc_url,
            extended_agent_card_url=extended_agent_card_url,
        )
        return app


@click.command()
@click.option("--host", default="localhost")
@click.option("--port", default=9999)
def main(host: str, port: int):

    task_store = InMemoryTaskStore()
    request_handler = DefaultRequestHandler(
        agent_executor=CoreAgentExecutor(1),
        task_store=task_store,
    )
    server = DatabaseA2AStarletteApplication(request_handler)
    uvicorn.run(server.build(), host=host, port=port)


if __name__ == "__main__":
    main()
