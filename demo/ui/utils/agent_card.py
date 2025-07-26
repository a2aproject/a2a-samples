import requests

from a2a.types import AgentCard


def get_agent_card(remote_agent_address: str) -> AgentCard:
    """Get the agent card."""
    if not remote_agent_address.startswith(('http://', 'https://')):
        remote_agent_address = 'http://' + remote_agent_address
    agent_card = requests.get(f'{remote_agent_address}/.well-known/agent.json')
    return AgentCard(**agent_card.json())
