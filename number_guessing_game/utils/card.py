"""utils.card
Utilities to construct minimal but spec-compliant A2A *AgentCard*
objects.
"""

from typing import Any, Dict, List


def make_agent_card(name: str, port: int) -> Dict[str, Any]:
    """Return a minimal AgentCard with a single *echo* skill."""

    return {
        "protocolVersion": "0.2.6",
        "name": name,
        "description": "Toy echo agent running locally",
        "url": f"http://localhost:{port}/a2a/v1",
        "preferredTransport": "JSONRPC",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": "echo",
                "name": "Echo",
                "description": "Echoes text back to the caller",
                "tags": ["demo"],
                "examples": ["hello"],
                "inputModes": ["text/plain"],
                "outputModes": ["text/plain"],
            }
        ],
    }


def build_complete_agent_card(
    name: str,
    port: int,
    *,
    description: str,
    skills: List[Dict[str, Any]],
    version: str = "0.1.0",
    protocol_version: str = "0.2.6",
    preferred_transport: str = "JSONRPC",
) -> Dict[str, Any]:
    """Return a fully populated AgentCard according to the spec."""

    return {
        "protocolVersion": protocol_version,
        "name": name,
        "description": description,
        "url": f"http://localhost:{port}/a2a/v1",
        "preferredTransport": preferred_transport,
        "version": version,
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": skills,
    } 