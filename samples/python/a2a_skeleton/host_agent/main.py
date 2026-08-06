import os
import sys
import httpx
import logging

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from dotenv import load_dotenv

from agent.agent_card import build_agent_card
from agent.agent_executor import HostAgentExecutor
from discovery.discovery import DiscoveryClient

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent_cards = []

async def on_startup():
    global agent_cards, request_handler
    discovery = DiscoveryClient()
    agent_cards.clear()
    agent_cards.extend(await discovery.list_agent_cards())
    # HostAgentExecutor를 새로 생성해서 request_handler에 할당
    request_handler.agent_executor = HostAgentExecutor(agent_cards)

# HostAgentExecutor에 agent_cards를 전달
request_handler = DefaultRequestHandler(
    agent_executor=HostAgentExecutor(agent_cards),
    task_store=InMemoryTaskStore(),
)

HOST = os.getenv('HOST')
PORT = int(os.getenv('PORT'))

server = A2AStarletteApplication(
    agent_card=build_agent_card(HOST, PORT),
    http_handler=request_handler,
)

app = server.build()

# Starlette/FastAPI의 startup 이벤트에 등록
if hasattr(app, "add_event_handler"):
    app.add_event_handler("startup", on_startup)
