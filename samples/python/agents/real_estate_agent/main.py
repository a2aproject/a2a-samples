import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from real_estate_agent.agent_card import agent_card
from real_estate_agent.agent_executor import RealEstateAgentExecutor
from real_estate_agent.middleware.auth import ApiKeyAuthMiddleware

request_handler = DefaultRequestHandler(
    agent_executor=RealEstateAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

server = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler,
)

app = server.build()
app.add_middleware(ApiKeyAuthMiddleware)


if __name__ == "__main__":
    uvicorn.run(app, host="::", port=3001)