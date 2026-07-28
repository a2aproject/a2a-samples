"""Tool authorization policy for the SAP Maintenance Agent.

Security goal: protect write actions while keeping read insights frictionless.
"""

from __future__ import annotations

import os

from dataclasses import dataclass

from app.agent_config import ENABLE_WRITE_ACTIONS, TOOL_POLICY_MODE


WRITE_TOOLS = {'set_orders_to_teco', 'reset_orders_teco'}


@dataclass
class PolicyDecision:
    """Result of a tool policy evaluation."""

    allowed: bool
    reason: str = ''


class ToolPolicyEngine:
    """Policy evaluator for tool execution.

    Modes (env `TOOL_POLICY_MODE`):
    - permissive (default): allow reads and writes
    - read_only: deny all write tools
    - strict: writes only when ENABLE_WRITE_ACTIONS=true
    """

    def __init__(self) -> None:
        self.mode = (
            os.getenv('TOOL_POLICY_MODE', TOOL_POLICY_MODE).strip().lower()
        )
        self.enable_writes = (
            os.getenv(
                'ENABLE_WRITE_ACTIONS',
                'true' if ENABLE_WRITE_ACTIONS else 'false',
            )
            .strip()
            .lower()
            == 'true'
        )

    def evaluate(self, tool_name: str) -> PolicyDecision:
        """Evaluate whether the given tool is allowed under the current policy."""
        if tool_name not in WRITE_TOOLS:
            return PolicyDecision(True, 'read tool allowed')
        if self.mode == 'read_only':
            return PolicyDecision(
                False, 'write actions disabled (read_only mode)'
            )
        if self.mode == 'strict' and not self.enable_writes:
            return PolicyDecision(False, 'write actions disabled by policy')
        return PolicyDecision(True, 'write tool allowed')
