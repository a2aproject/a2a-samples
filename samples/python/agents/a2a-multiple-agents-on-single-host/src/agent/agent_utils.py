from typing import Callable

from a2a.types import AgentCard
from fastapi import FastAPI
from google.adk.agents import LlmAgent

from src.a2a.a2a_fastapi_app import get_agent_request_handler, A2AFastApiApp


def setup_agent(name: str,
                get_agent: Callable[[str], LlmAgent],
                get_agent_card: Callable[[str], AgentCard],
                model_name: str,
                agent_base_url: str,
                app: FastAPI
                ) -> None:
    agent = get_agent(model_name)
    agent_request_handler = get_agent_request_handler(agent)
    agent_card = get_agent_card(f"{agent_base_url}/{name}/")
    agent_server = A2AFastApiApp(fastapi_app=app, agent_card=agent_card,
                                 http_handler=agent_request_handler)
    agent_server.build(rpc_url=f"/{name}/", agent_card_url=f"/{name}/{{path:path}}")
