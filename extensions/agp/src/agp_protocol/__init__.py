import logging

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Core Data Structures ---


class CapabilityAnnouncement(BaseModel):
    """Data structure for a service announcement by a Gateway Agent."""

    capability: str = Field(
        ...,
        description="The function or skill provided (e.g., 'financial_analysis:quarterly').",
    )
    version: str = Field(..., description='Version of the capability schema.')
    cost: float | None = Field(None, description='Estimated cost metric.')
    policy: dict[str, Any] = Field(
        ...,
        description='Key-value pairs defining required security/data policies.',
    )

    model_config = ConfigDict(extra='forbid')


class IntentPayload(BaseModel):
    """The request payload routed by AGP."""

    target_capability: str = Field(
        ..., description='The capability the Intent seeks to fulfill.'
    )
    payload: dict[str, Any] = Field(
        ..., description='The core data arguments required for the task.'
    )
    # FIX APPLIED: Renaming internal field to policy_constraints for clarity
    policy_constraints: dict[str, Any] = Field(
        default_factory=dict,
        description='Client-defined constraints that must be matched against the announced policy.',
        alias='policy_constraints',
    )

    model_config = ConfigDict(extra='forbid', populate_by_name=True)


# --- AGP Routing Structures ---


class RouteEntry(BaseModel):
    """A single possible route to fulfill a fulfill a capability."""

    path: str = Field(
        ...,
        description="The destination Squad/API path (e.g., 'Squad_Finance/gateway').",
    )
    cost: float = Field(..., description='Cost metric for this route.')
    policy: dict[str, Any] = Field(
        ...,
        description='Policies of the destination, used for matching Intent constraints.',
    )


class AGPTable(BaseModel):
    """The central routing table maintained by a Gateway Agent."""

    routes: dict[str, list[RouteEntry]] = Field(default_factory=dict)

    model_config = ConfigDict(extra='forbid')


# --- Core AGP Routing Logic ---


class AgentGatewayProtocol:
    """
    Simulates the core functions of an Autonomous Squad Gateway Agent.
    Handles Capability Announcements and Policy-Based Intent Routing.
    The primary routing logic is in _select_best_route to allow easy overriding via subclassing.
    """

    def __init__(self, squad_name: str, agp_table: AGPTable):
        self.squad_name = squad_name
        self.agp_table = agp_table

    def announce_capability(
        self, announcement: CapabilityAnnouncement, path: str
    ):
        """Simulates receiving a capability announcement and updating the AGP Table."""
        entry = RouteEntry(
            path=path,
            cost=announcement.cost or 0.0,
            policy=announcement.policy,
        )

        capability_key = announcement.capability

        # Use setdefault to initialize the list if the key is new
        self.agp_table.routes.setdefault(capability_key, []).append(entry)

        print(
            f'[{self.squad_name}] ANNOUNCED: {capability_key} routed via {path}'
        )

    # Protected method containing the core, overridable routing logic
    def _select_best_route(self, intent: IntentPayload) -> RouteEntry | None:
        """
        Performs Policy-Based Routing to find the best available squad.

        Routing Logic:
        1. Find all routes matching the target_capability.
        2. Filter routes based on matching all policy constraints (PBR).
        3. Select the lowest-cost route among the compliant options.
        """
        target_cap = intent.target_capability
        # CRITICAL CHANGE: Use the correct snake_case attribute name for constraints
        intent_constraints = intent.policy_constraints

        if target_cap not in self.agp_table.routes:
            logging.warning(
                f"[{self.squad_name}] ROUTING FAILED: Capability '{target_cap}' is unknown."
            )
            return None

        possible_routes = self.agp_table.routes[target_cap]

        # --- 2. Policy Filtering (Optimized using list comprehension and all()) ---
        compliant_routes = [
            route
            for route in possible_routes
            if all(
                # Check if the constraint key exists in the route policy AND the values are sufficient.
                key in route.policy
                and (
                    # If the key is 'security_level' and both values are numeric, check for >= sufficiency.
                    route.policy[key] >= value
                    if key == 'security_level'
                    and isinstance(route.policy.get(key), (int, float))
                    and isinstance(value, (int, float))
                    # Otherwise (e.g., boolean flags like 'requires_PII'), require exact equality.
                    else route.policy[key] == value
                )
                for key, value in intent_constraints.items()
            )
        ]

        if not compliant_routes:
            logging.warning(
                f'[{self.squad_name}] ROUTING FAILED: No compliant route found for constraints: {intent_constraints}'
            )
            return None

        # --- 3. Best Route Selection (Lowest Cost) ---
        best_route = min(compliant_routes, key=lambda r: r.cost)

        return best_route

    # Public method that is typically called by the A2A endpoint
    def route_intent(self, intent: IntentPayload) -> RouteEntry | None:
        """
        Public entry point for routing an Intent payload.
        Calls the internal selection logic and prints the result.
        """
        best_route = self._select_best_route(intent)

        if best_route:
            print(
                f"[{self.squad_name}] ROUTING SUCCESS: Intent for '{intent.target_capability}' routed to {best_route.path} (Cost: {best_route.cost})"
            )
        return best_route
