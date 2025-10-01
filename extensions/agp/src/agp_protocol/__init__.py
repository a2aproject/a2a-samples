import json
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
import logging

# --- Core Data Structures (Matching AGP Specification) ---

class CapabilityAnnouncement(BaseModel):
    """Data structure for a service announcement by a Gateway Agent."""
    capability: str = Field(..., description="The function or skill provided (e.g., 'financial_analysis:quarterly').")
    version: str = Field(..., description="Version of the capability schema.")
    cost: Optional[float] = Field(None, description="Estimated cost metric.")
    policy: Dict[str, Any] = Field(..., description="Key-value pairs defining required security/data policies.")
    
    model_config = ConfigDict(extra='forbid')

class IntentPayload(BaseModel):
    """The request payload routed by AGP."""
    target_capability: str = Field(..., description="The capability the Intent seeks to fulfill.")
    payload: Dict[str, Any] = Field(..., description="The core data arguments for the task.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Client-defined constraints for policy matching.")

    model_config = ConfigDict(extra='forbid')

# --- AGP Routing Structures (AGP Spec 3) ---

class RouteEntry(BaseModel):
    """A single possible route to fulfill a capability."""
    path: str = Field(..., description="The destination Squad/API path (e.g., 'Squad_Finance/gateway').")
    cost: float = Field(..., description="Cost metric for this route.")
    policy: Dict[str, Any] = Field(..., description="Policies of the destination, used for matching Intent constraints.")

class AGPTable(BaseModel):
    """The central routing table maintained by a Gateway Agent."""
    # Key: capability string (e.g., 'billing:invoice:generate')
    # Value: List of possible RouteEntry objects
    routes: Dict[str, List[RouteEntry]] = Field(default_factory=dict)
    
    model_config = ConfigDict(extra='allow') # Allow dynamic capability keys

# --- Core AGP Routing Logic ---

class AgentGatewayProtocol:
    """
    Simulates the core functions of an Autonomous Squad Gateway Agent.
    Handles Capability Announcements and Policy-Based Intent Routing.
    """
    
    def __init__(self, squad_name: str, agp_table: AGPTable):
        self.squad_name = squad_name
        self.agp_table = agp_table

    def announce_capability(self, announcement: CapabilityAnnouncement, path: str):
        """Simulates receiving a capability announcement and updating the AGP Table."""
        entry = RouteEntry(
            path=path,
            cost=announcement.cost or 0.0,
            policy=announcement.policy
        )
        
        capability_key = announcement.capability
        
        if capability_key not in self.agp_table.routes:
            self.agp_table.routes[capability_key] = []
            
        # Simplistic: just add the route entry
        self.agp_table.routes[capability_key].append(entry)
        logging.info(f"[{self.squad_name}] ANNOUNCED: {capability_key} routed via {path}")


    def route_intent(self, intent: IntentPayload) -> Optional[RouteEntry]:
        """
        Performs Policy-Based Routing to find the best available squad.
        
        Routing Logic:
        1. Find all routes matching the target_capability.
        2. Filter routes based on matching all policy constraints (Intent metadata must match Route policy).
        3. Select the lowest-cost route among the compliant options.
        """
        target_cap = intent.target_capability
        intent_constraints = intent.metadata
        
        if target_cap not in self.agp_table.routes:
            logging.warning(f"[{self.squad_name}] ROUTING FAILED: Capability '{target_cap}' is unknown.")
            return None

        possible_routes = self.agp_table.routes[target_cap]
        compliant_routes: List[RouteEntry] = []
        
        # --- 2. Policy Filtering ---
        for route in possible_routes:
            is_compliant = True
            
            # Check if all Intent metadata constraints are satisfied by the Route's policy
            for constraint_key, intent_value in intent_constraints.items():
                if constraint_key not in route.policy or route.policy[constraint_key] != intent_value:
                    # If the intent requires a policy (like requires_PII: true) 
                    # and the route either lacks that policy key or the value doesn't match, it fails compliance.
                    is_compliant = False
                    break
            
            if is_compliant:
                compliant_routes.append(route)

        if not compliant_routes:
            logging.warning(f"[{self.squad_name}] ROUTING FAILED: No compliant route found for constraints: {intent_constraints}")
            return None

        # --- 3. Best Route Selection (Lowest Cost) ---
        best_route = min(compliant_routes, key=lambda r: r.cost)
        
        logging.info(f"[{self.squad_name}] ROUTING SUCCESS: Intent for '{target_cap}' routed to {best_route.path} (Cost: {best_route.cost})")
        return best_route

