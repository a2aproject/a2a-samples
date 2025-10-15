from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
import logging

# NOTE: Since this file is now in the src/agp_protocol package, 
# we use relative import to pull necessary classes from the sibling file (__init__.py).
from .__init__ import ( 
    AgentGatewayProtocol,
    IntentPayload,
    RouteEntry,
)

# --- NEW DELEGATION INTENT STRUCTURES ---

class SubIntent(BaseModel):
    """
    An atomic, routable sub-task created during decomposition.
    
    This structure uses 'policy_constraints' for clarity.
    """
    
    target_capability: str = Field(
        ..., description="The specific AGP capability to route (e.g., 'infra:provision')."
    )
    payload: Dict[str, Any] = Field(
        ..., description="Data specific to the sub-intent (e.g., VM type, budget amount)."
    )
    policy_constraints: Dict[str, Any] = Field(
        default_factory=dict,
        description="Specific security/geo constraints for this individual sub-task.",
    )

    model_config = ConfigDict(extra='forbid')


class DelegationIntent(BaseModel):
    """A high-level meta-task requiring decomposition and routing to multiple squads."""
    
    meta_task: str = Field(..., description="High-level goal (e.g., 'Setup Project Alpha').")
    sub_intents: List[SubIntent] = Field(
        ..., description="List of atomic tasks to be decomposed and routed."
    )
    origin_squad: str = Field(..., description="The squad initiating the request (e.g., 'HR').")

    model_config = ConfigDict(extra='forbid')


# --- SIMULATION SPECIFIC DELEGATION ROUTER ---

class DelegationRouter:
    """
    Manages the overall decomposition of a meta-task into routable SubIntents
    and aggregates the final results from the AGP Gateway.
    """

    def __init__(self, central_gateway: AgentGatewayProtocol): 
        self.central_gateway = central_gateway
        # Access the squad_name attribute from the Gateway instance
        self.squad_name = central_gateway.squad_name 

    def route_delegation_intent(self, delegation_intent: DelegationIntent):
        """
        Simulates the Central Gateway receiving a meta-task, decomposing it, and routing 
        each component through the core AGP Policy-Based Router.
        """
        
        print(f"\n[{self.squad_name}] RECEIVED DELEGATION: '{delegation_intent.meta_task}' from {delegation_intent.origin_squad}")
        print("--------------------------------------------------------------------------------")
        
        results = {}
        
        for i, sub_intent_data in enumerate(delegation_intent.sub_intents):
            
            # --- CRITICAL DECOMPOSITION STEP ---
            # Synthesize a simple AGP IntentPayload from the SubIntent data
            sub_intent = IntentPayload(
                target_capability=sub_intent_data.target_capability,
                payload=sub_intent_data.payload,
                # Use the correct keyword for the core IntentPayload
                policy_constraints=sub_intent_data.policy_constraints, 
            )
            
            # FIX APPLIED: Call the new PUBLIC method (select_best_route) 
            # to respect encapsulation and perform routing without side effects.
            route = self.central_gateway.select_best_route(sub_intent)
            
            status = "SUCCESS" if route else "FAILED"
            path = route.path if route else "N/A"
            cost = route.cost if route else "N/A"
            
            print(f"[{i+1}/{len(delegation_intent.sub_intents)}] TASK: {sub_intent.target_capability}")
            print(f"    STATUS: {status}")
            print(f"    ROUTE: {path} (Cost: {cost})")
            
            results[sub_intent.target_capability] = status
            
        print("--------------------------------------------------------------------------------")
        print(f"[{self.squad_name}] DELEGATION COMPLETE: Processed {len(results)} sub-tasks.")
        return results
