from typing import Optional, Dict, Any, List, Callable
from pydantic import BaseModel, Field, ConfigDict
import logging


# --- Core Data Structures ---


class CapabilityAnnouncement(BaseModel):
    """Data structure for a service announcement by a Gateway Agent."""

    capability: str = Field(
        ...,
        description="The function or skill provided (e.g., 'financial_analysis:quarterly').",
    )
    version: str = Field(..., description="Version of the capability schema.")
    cost: Optional[float] = Field(None, description="Estimated cost metric.")
    policy: Dict[str, Any] = Field(
        ..., description="Key-value pairs defining required security/data policies."
    )

    model_config = ConfigDict(extra='forbid')


class IntentPayload(BaseModel):
    """The request payload routed by AGP."""

    target_capability: str = Field(
        ..., description="The capability the Intent seeks to fulfill."
    )
    payload: Dict[str, Any] = Field(
        ..., description="The core data arguments required for the task."
    )
    # This field holds the constraints the client demands (e.g., security_level: 5)
    policy_constraints: Dict[str, Any] = Field(
        default_factory=dict,
        description="Client-defined constraints that must be matched against the announced policy.",
    )

    model_config = ConfigDict(extra='forbid')


# --- AGP Routing Structures ---


class RouteEntry(BaseModel):
    """A single possible route to fulfill a fulfill a capability."""

    path: str = Field(
        ..., description="The destination Squad/API path (e.g., 'Squad_Finance/gateway')."
    )
    cost: float = Field(..., description="Cost metric for this route.")
    policy: Dict[str, Any] = Field(
        ...,
        description="Policies of the destination, used for matching Intent constraints.",
    )


class AGPTable(BaseModel):
    """The central routing table maintained by a Gateway Agent."""

    routes: Dict[str, List[RouteEntry]] = Field(default_factory=dict)

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

    def announce_capability(self, announcement: CapabilityAnnouncement, path: str):
        """Simulates receiving a capability announcement and updating the AGP Table."""
        entry = RouteEntry(
            path=path,
            cost=announcement.cost or 0.0,
            policy=announcement.policy,
        )

        capability_key = announcement.capability

        # Use setdefault to initialize the list if the key is new
        self.agp_table.routes.setdefault(capability_key, []).append(entry)

        print(f"[{self.squad_name}] ANNOUNCED: {capability_key} routed via {path}")

    # Private method containing the core, *unmodified* routing logic
    def __select_best_route(self, intent: IntentPayload) -> Optional[RouteEntry]:
        """
        [Private Logic] Performs Policy-Based Routing to find the best available squad.
        """
        target_cap = intent.target_capability
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
                key in route.policy
                and (
                    route.policy[key] >= value
                    if key == 'security_level'
                    and isinstance(route.policy.get(key), (int, float))
                    and isinstance(value, (int, float))
                    else route.policy[key] == value
                )
                for key, value in intent_constraints.items()
            )
        ]

        if not compliant_routes:
            logging.warning(
                f"[{self.squad_name}] ROUTING FAILED: No compliant route found for constraints: {intent_constraints}"
            )
            return None

        # --- 3. Best Route Selection (Lowest Cost) ---
        best_route = min(compliant_routes, key=lambda r: r.cost)

        return best_route

    # Public, overridable method for core routing logic (used by external components)
    def select_best_route(self, intent: IntentPayload) -> Optional[RouteEntry]:
        """
        Public entry point for external components (like DelegationRouter) 
        to retrieve the best route *without side effects*.
        """
        return self.__select_best_route(intent)

    # Public method that is typically called by the A2A endpoint (includes side effects)
    def route_intent(self, intent: IntentPayload) -> Optional[RouteEntry]:
        """
        Public entry point for routing an Intent payload, including printing side effects.
        """
        best_route = self.__select_best_route(intent)

        if best_route:
            print(
                f"[{self.squad_name}] ROUTING SUCCESS: Intent for '{intent.target_capability}' routed to {best_route.path} (Cost: {best_route.cost})"
            )
        return best_route

        
