import logging
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from src.a2a.a2a_fastapi_app import A2AFastApiApp, get_agent_request_handler
from src.agent.analyzer_agent import analyzer_agent, get_analyzer_agent_card
from src.agent.conversation_agent import get_conversational_agent_card, conversational_agent
from src.agent.trending_topics_agent import trending_topics_agent, get_trending_topics_agent_card

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

AGENT_BASE_URL = os.getenv('AGENT_BASE_URL')
logger.info(f"AGENT BASE URL {AGENT_BASE_URL}")

app: FastAPI = FastAPI(title="Run multiple agents on single host using A2A protocol.",
                       description="Run multiple agents on single host using A2A protocol.",
                       version="1.0.0",
                       root_path=f"/a2a")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


conversation_agent_request_handler = get_agent_request_handler(conversational_agent)
conversational_agent_card = get_conversational_agent_card(f"{AGENT_BASE_URL}/conversation/")
conversational_agent_server = A2AFastApiApp(fastapi_app=app, agent_card=conversational_agent_card, http_handler=conversation_agent_request_handler)
# {path:path} added into the agent card url path to handle both 'agent-card.json' and '/.well-known/agent-card.json'
conversational_agent_server.build(rpc_url="/conversation/", agent_card_url="/conversation/{path:path}")

trending_agent_request_handler = get_agent_request_handler(trending_topics_agent)
trending_topics_agent_card = get_trending_topics_agent_card(f"{AGENT_BASE_URL}/trending/")
trending_agent_server = A2AFastApiApp(fastapi_app=app, agent_card=trending_topics_agent_card,
                                      http_handler=trending_agent_request_handler)
trending_agent_server.build(rpc_url="/trending/", agent_card_url="/trending/{path:path}")

analyzer_agent_request_handler = get_agent_request_handler(analyzer_agent)
analyzer_agent_card = get_analyzer_agent_card(f"{AGENT_BASE_URL}/analyzer/")
analyzer_agent_server = A2AFastApiApp(fastapi_app=app, agent_card=analyzer_agent_card,
                                      http_handler=analyzer_agent_request_handler)
analyzer_agent_server.build(rpc_url="/analyzer/", agent_card_url="/analyzer/{path:path}")

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)
