# Import libraries
from typing import Any, List

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from a2a_servers.common.agent_task_manager import AgentTaskManager
from a2a_servers.common.types import AgentCapabilities, AgentCard, AgentSkill


def generate_agent_card(
    agent_name: str,
    agent_description: str,
    agent_url: str,
    agent_version: str,
    can_stream: bool = False,
    can_push_notifications: bool = False,
    can_state_transition_history: bool = True,
    authentication: str = None,
    default_input_modes: List[str] = ["text"],
    default_output_modes: List[str] = ["text"],
    skills: List[AgentSkill] = None,
):
    """
    Generates an agent card.

    Returns:
        AgentCard: An instance of AgentCard containing agent details.
    """

    return AgentCard(
        name=agent_name,
        description=agent_description,
        url=agent_url,
        version=agent_version,
        capabilities=AgentCapabilities(
            streaming=can_stream,
            pushNotifications=can_push_notifications,
            stateTransitionHistory=can_state_transition_history,
        ),
        authentication=authentication,
        defaultInputModes=default_input_modes,
        defaultOutputModes=default_output_modes,
        skills=skills,
    )


def generate_agent_task_manager(agent: Any):
    """
    Generates an instance of AgentTaskManager for the given agent.
    """
    return AgentTaskManager(agent)