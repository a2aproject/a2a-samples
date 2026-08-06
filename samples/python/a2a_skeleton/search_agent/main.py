import os
import sys
import httpx
import logging

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from agent.agent_card import build_agent_card
from agent.agent_executor import SearchAgentExecutor
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

request_handler = DefaultRequestHandler(
    agent_executor=SearchAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

HOST = os.getenv('HOST')
PORT = int(os.getenv('PORT'))

server = A2AStarletteApplication(
    agent_card=build_agent_card(HOST, PORT),
    http_handler=request_handler,
)

app = server.build()