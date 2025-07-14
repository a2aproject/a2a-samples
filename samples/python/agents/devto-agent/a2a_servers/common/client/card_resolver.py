import re

import httpx
from a2a_servers.common.types import (
    AgentCard,
    A2AClientJSONError,
)
import json


class A2ACardResolver:
    def __init__(self, base_url, agent_card_path="/.well-known/agent.json"):
        self.base_url = base_url
        self.agent_card_path = agent_card_path.lstrip("/")

    def get_agent_card(self) -> AgentCard:
        with httpx.Client() as client:
            url = re.match(r'(https?://[^/]+)', self.base_url).group(1).rstrip("/")
            response = client.get(url + "/" + self.agent_card_path)
            response.raise_for_status()
            try:
                resp_dict = response.json()
                resp_dict['url'] = self.base_url
                return AgentCard(**resp_dict)
            except json.JSONDecodeError as e:
                raise A2AClientJSONError(str(e)) from e
