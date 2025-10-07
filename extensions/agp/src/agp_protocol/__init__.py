from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
import logging


# --- Core Data Structures ---

# NEW: Defines the standardized policy structure
class PolicySchema(BaseModel):
    """
    Standardized, optional policy schema used by enterprises to enforce
    security, geo-location, and compliance rules across the squad hierarchy.
    """
    security_level: Optional[int] = Field(None, description="Minimum security level required/offered (e.g., 3, 5, 7).")
    requires_pii: Optional[bool] = Field(None, description="Whether the policy requires PII handling capability (True/False).")
    geo: Optional[str] = Field(None, description="Geographical restrictions (e.g., 'US', 'EU').")
    
    # Allows additional custom policy fields to be included
    model_config = ConfigDict(extra='allow') 


class CapabilityAnnouncement(BaseModel):
    """Data structure for a service announcement by a Gateway Agent."""

    capability: str = Field(
        ...,
        description="The function or skill provided (e.g., 'financial_analysis:quarterly').",
    )
    version: str = Field(..., description="Version of the capability schema.")
    cost: Optional[float] = Field(None, description="Estimated cost metric.")
    # UPDATED: Policy is now an instance of PolicySchema
    policy: PolicySchema = Field(
        ..., description="Standardized security and compliance policies for the capability."
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
    # UPDATED: Intent metadata is now PolicySchema to enforce constraints
    metadata: PolicySchema = Field(
        default_factory=PolicySchema,
        description="Client-defined policy constraints that must be matched against the announced policy.",
    )

    model_config = ConfigDict(extra='forbid')


# --- AGP Routing Structures ---


class RouteEntry(BaseModel):
    """A single possible route to fulfill a fulfill a capability."""

    path: str = Field(
        ..., description="The destination Squad/API path (e.g., 'Squad_Finance/gateway')."
    )
    cost: float = Field(..., description="Cost metric for this route.")
    # UPDATED: Policy is now an instance of PolicySchema
    policy: PolicySchema = Field(
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
            # Policy is already PolicySchema instance
            policy=announcement.policy,
        )

        capability_key = announcement.capability

        # Use setdefault to initialize the list if the key is new
        self.agp_table.routes.setdefault(capability_key, []).append(entry)

        print(f"[{self.squad_name}] ANNOUNCED: {capability_key} routed via {path}")

    def route_intent(self, intent: IntentPayload) -> Optional[RouteEntry]:
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
    
    # Protected method containing the core, overridable routing logic
    def _select_best_route(self, intent: IntentPayload) -> Optional[RouteEntry]:
        """
        Performs Policy-Based Routing to find the best available squad.
        
        Routing Logic:
        1. Find all routes matching the target_capability.
        2. Filter routes based on matching all policy constraints (PBR).
        3. Select the lowest-cost route among the compliant options.
        """
        target_cap = intent.target_capability
        # CRITICAL CHANGE: Use intent.metadata.model_dump(exclude_none=True) 
        # to iterate only over constraints that were explicitly set by the client.
        intent_constraints = intent.metadata.model_dump(exclude_none=True) 

        if target_cap not in self.agp_table.routes:
            logging.warning(
                f"[{self.squad_name}] ROUTING FAILED: Capability '{target_cap}' is unknown."
            )
            return None

        possible_routes = self.agp_table.routes[target_cap]

        # --- 2. Policy Filtering (Robust Logic Applied Here) ---
        compliant_routes = [
            route
            for route in possible_routes
            if all(
                # Use route.policy.model_dump() to treat route policy as a dictionary
                key in route.policy.model_dump()
                and (
                    # If the key is 'security_level' and both values are numeric, check for >= sufficiency.
                    route.policy.model_dump().get(key) >= value
                    if key == 'security_level'
                    and isinstance(route.policy.model_dump().get(key), (int, float))
                    and isinstance(value, (int, float))
                    # Otherwise (e.g., boolean flags like 'requires_PII'), require exact equality.
                    else route.policy.model_dump().get(key) == value
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
