import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from collections import OrderedDict

# --- Configuration & Constants ---
SAGA_EXTENSION_URI = "https://a2a.dev/extensions/saga/v1"
A2A_EXTENSION_HEADER_KEY = "A2A-Extensions"

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SagaOrchestrator")

# --- Mocks for A2A SDK (Replace with actual imports in production) ---
class A2AClient:
    """
    Mock client simulating JSON-RPC calls to remote agents.
    In a real implementation, this would be `a2a.Client`.
    """
    async def call_method(self, url: str, method: str, params: Dict, headers: Dict) -> Dict:
        """
        Simulates the network call.
        Replace this with actual HTTP/JSON-RPC transport logic.
        """
        logger.info(f"--> OUTBOUND RPC: {method} to {url}")
        logger.debug(f"    Params: {json.dumps(params)}")
        logger.debug(f"    Headers: {json.dumps(headers)}")
        
        # SIMULATION LOGIC FOR TEST VECTOR A + B (RFC Appendix B)
        idempotency_key = None
        if method == "saga.step.execute":
            idempotency_key = params.get("execute", {}).get("idempotency_key")
        elif method == "saga.step.compensate":
            idempotency_key = params.get("compensate", {}).get("idempotency_key")

        if idempotency_key in getattr(self, "_idempotency_store", {}):
            return self._idempotency_store[idempotency_key]

        step_id = params.get("step_id", "")

        if step_id == "reserve_username" and method == "saga.step.execute":
            response = {"status": "succeeded", "evidence": {"reservation_id": "resv-001"}}
        elif step_id == "create_customer_record" and method == "saga.step.execute":
            response = {"status": "succeeded", "evidence": {"customer_row_id": "crm-777"}}
        elif step_id == "provision_workspace" and method == "saga.step.execute":
            if idempotency_key and idempotency_key.endswith(":retry-1"):
                response = {
                    "status": "failed",
                    "failure": {
                        "failure_class": "deterministic",
                        "reason": "Plan not available"
                    }
                }
            else:
                response = {
                    "status": "unknown",
                    "failure": {
                        "failure_class": "unknown",
                        "reason": "timeout after dispatch"
                    }
                }
        elif step_id == "provision_workspace" and method == "saga.step.verify":
            response = {"status": "not_verified", "details": {"workspace": None}}
        elif step_id == "reserve_username" and method == "saga.step.compensate":
            response = {"status": "compensated", "evidence": {"released": True}}
        elif step_id == "create_customer_record" and method == "saga.step.compensate":
            response = {"status": "compensated", "evidence": {"deleted": True}}
        else:
            response = {"status": "succeeded", "evidence": {}}

        if idempotency_key:
            if not hasattr(self, "_idempotency_store"):
                self._idempotency_store = {}
            self._idempotency_store[idempotency_key] = response

        return response

# --- Data Structures ---

@dataclass(frozen=True)
class ActionSpec:
    action: str
    args: Dict[str, Any]


@dataclass(frozen=True)
class ExecuteSpec(ActionSpec):
    idempotency_key: str


@dataclass(frozen=True)
class CompensateSpec(ActionSpec):
    idempotency_key: str


@dataclass(frozen=True)
class StepDefinition:
    step_id: str
    participant: str
    execute: ExecuteSpec
    reversibility: str
    criticality: str
    group: Optional[str] = None
    verify: Optional[ActionSpec] = None
    compensate: Optional[CompensateSpec] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class SagaDefinition:
    saga_id: str
    goal: str
    steps: List[StepDefinition]
    policy: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class SagaContext:
    saga_id: str
    history: List[Dict] = field(default_factory=list)
    applied_steps_by_group: "OrderedDict[str, List[StepDefinition]]" = field(default_factory=OrderedDict)
    retry_counts: Dict[str, int] = field(default_factory=dict)

class StepResult(Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"

# --- The Orchestrator Implementation ---

class SagaOrchestrator:
    def __init__(self, client: A2AClient):
        self.client = client

    def _get_headers(self) -> Dict[str, str]:
        """
        Normative Requirement: 5.1 Header Negotiation
        """
        return {
            "Content-Type": "application/json",
            A2A_EXTENSION_HEADER_KEY: SAGA_EXTENSION_URI
        }

    async def run_saga(self, saga_def: SagaDefinition):
        """
        Main entry point for executing a Saga.
        """
        saga_id = saga_def.saga_id
        steps = saga_def.steps
        ctx = SagaContext(saga_id=saga_id)

        logger.info(f"Starting Saga {saga_id}")

        # 1. Group steps by 'group' ID for parallel execution
        # Logic: Sequential groups, parallel steps within groups.
        grouped_steps = self._group_steps(steps)
        ctx.applied_steps_by_group = OrderedDict((gid, []) for gid in grouped_steps.keys())

        try:
            for group_id, group_steps in grouped_steps.items():
                logger.info(f"Executing Group: {group_id} ({len(group_steps)} steps)")
                
                # Execute group in parallel (O1 Conformance)
                results = await asyncio.gather(*[
                    self._execute_step(ctx, step, group_id) for step in group_steps
                ])

                # Check for failures in the group
                failed_results = [r for r in results if r["status"] != StepResult.SUCCEEDED.value]
                
                if failed_results:
                    logger.error(f"Group {group_id} failed. Initiating Compensation.")
                    raise Exception(f"Saga Failed at group {group_id}: {failed_results[0]}")

            logger.info(f"Saga {saga_id} Completed Successfully!")
            return {"status": "completed", "ctx": ctx}

        except Exception as e:
            logger.warning(f"Aborting Saga: {e}")
            await self._compensate_saga(ctx)
            return {"status": "compensated", "error": str(e)}

    def _group_steps(self, steps: List[StepDefinition]) -> Dict[str, List[StepDefinition]]:
        """Helper to preserve order of groups but allow parallel steps within."""
        groups = OrderedDict()
        for step in steps:
            g_id = step.group or f"default_{step.step_id}"
            if g_id not in groups:
                groups[g_id] = []
            groups[g_id].append(step)
        return groups

    async def _execute_step(self, ctx: SagaContext, step: StepDefinition, group_id: str) -> Dict:
        """
        Executes a single step, handling Idempotency, Headers, and Unknown outcomes.
        """
        step_id = step.step_id

        # Normative Requirement: 9.1 Idempotency Keys
        if not step.execute.idempotency_key:
            raise ValueError(f"Missing execute.idempotency_key for step {step_id}")

        payload = {
            "saga_id": ctx.saga_id,
            "step_id": step_id,
            "execute": {
                "action": step.execute.action,
                "args": step.execute.args,
                "idempotency_key": step.execute.idempotency_key
            }
        }

        # RPC Call
        response = await self.client.call_method(
            url=step.participant,
            method="saga.step.execute",
            params=payload,
            headers=self._get_headers()
        )

        status = response.get("status")

        # Normative Requirement: 8.2 Verify Unknown Outcomes
        if status == StepResult.UNKNOWN.value and step.verify is not None:
            logger.info(f"Step {step_id} returned UNKNOWN. Verifying...")
            verification = await self._verify_step(ctx, step)
            if verification["status"] == "verified":
                status = StepResult.SUCCEEDED.value
            elif verification["status"] == "not_verified":
                logger.info(f"Verification failed for {step_id}. Retrying execute once.")
                response = await self._retry_execute_step(ctx, step)
                status = response.get("status")

        if status in (StepResult.FAILED.value, StepResult.UNKNOWN.value, "pending_approval"):
            response.setdefault("failure", {
                "failure_class": "unknown",
                "reason": "unspecified failure"
            })

        # Record success for potential future compensation
        if status == StepResult.SUCCEEDED.value:
            ctx.applied_steps_by_group[group_id].append(step)
            
        return {"step_id": step_id, "status": status, "raw": response}

    async def _verify_step(self, ctx: SagaContext, step: StepDefinition) -> Dict:
        if step.verify is None:
            raise ValueError(f"Missing verify action for step {step.step_id}")

        payload = {
            "saga_id": ctx.saga_id,
            "step_id": step.step_id,
            "verify": {
                "action": step.verify.action,
                "args": step.verify.args
            }
        }
        return await self.client.call_method(
            url=step.participant,
            method="saga.step.verify",
            params=payload,
            headers=self._get_headers()
        )

    async def _retry_execute_step(self, ctx: SagaContext, step: StepDefinition) -> Dict:
        step_id = step.step_id
        retry_count = ctx.retry_counts.get(step_id, 0) + 1
        ctx.retry_counts[step_id] = retry_count

        retry_payload = {
            "saga_id": ctx.saga_id,
            "step_id": step_id,
            "execute": {
                "action": step.execute.action,
                "args": step.execute.args,
                "idempotency_key": f"{step.execute.idempotency_key}:retry-{retry_count}"
            }
        }

        return await self.client.call_method(
            url=step.participant,
            method="saga.step.execute",
            params=retry_payload,
            headers=self._get_headers()
        )

    async def _compensate_saga(self, ctx: SagaContext):
        """
        Normative Requirement: 7.3 Compensation Ordering
        Executes compensation in Reverse Order (LIFO).
        """
        logger.info("--- STARTING COMPENSATION PHASE ---")

        # Reverse group order; parallel within a group.
        for group_id in reversed(list(ctx.applied_steps_by_group.keys())):
            group_steps = ctx.applied_steps_by_group[group_id]
            if not group_steps:
                continue
            await asyncio.gather(*[
                self._compensate_step(ctx, step) for step in group_steps
            ])
        
        logger.info("--- COMPENSATION COMPLETE ---")

    async def _compensate_step(self, ctx: SagaContext, step: StepDefinition):
        if step.compensate is None:
            logger.warning(f"Skipping step {step.step_id} (No compensation defined)")
            return

        step_id = step.step_id
        if not step.compensate.idempotency_key:
            raise ValueError(f"Missing compensate.idempotency_key for step {step_id}")

        payload = {
            "saga_id": ctx.saga_id,
            "step_id": step_id,
            "compensate": {
                "action": step.compensate.action,
                "args": step.compensate.args,
                "idempotency_key": step.compensate.idempotency_key
            }
        }

        logger.info(f"Compensating {step_id}...")
        await self.client.call_method(
            url=step.participant,
            method="saga.step.compensate",
            params=payload,
            headers=self._get_headers()
        )

# --- Test Vector Runner ---

async def main():
    client = A2AClient()
    orchestrator = SagaOrchestrator(client)
  
     # Define the Saga from Test Vector A (Appendix B.2)
    saga_definition = SagaDefinition(
        saga_id="tvA-saga-001",
        goal="Onboard customer c123",
        steps=[
            # Group 1: Parallel
            StepDefinition(
                step_id="reserve_username",
                group="g1",
                participant="a2a://agent/identity",
                execute=ExecuteSpec(
                    action="reserve_username",
                    args={"customer_id": "c123", "username": "acme"},
                    idempotency_key="tvA-saga-001:reserve_username:exec"
                ),
                compensate=CompensateSpec(
                    action="release_username",
                    args={"username": "acme"},
                    idempotency_key="tvA-saga-001:reserve_username:comp"
                ),
                verify=ActionSpec(
                    action="get_reservation",
                    args={"username": "acme"}
                ),
                reversibility="full",
                criticality="medium"
            ),
            StepDefinition(
                step_id="create_customer_record",
                group="g1",
                participant="a2a://agent/crm",
                execute=ExecuteSpec(
                    action="create_customer",
                    args={"customer_id": "c123", "name": "ACME"},
                    idempotency_key="tvA-saga-001:create_customer_record:exec"
                ),
                compensate=CompensateSpec(
                    action="delete_customer",
                    args={"customer_id": "c123"},
                    idempotency_key="tvA-saga-001:create_customer_record:comp"
                ),
                reversibility="full",
                criticality="high"
            ),
            # Group 2: Dependent (Will Fail)
            StepDefinition(
                step_id="provision_workspace",
                group="g2",
                participant="a2a://agent/provision",
                execute=ExecuteSpec(
                    action="provision_workspace",
                    args={"customer_id": "c123", "plan": "pro"},
                    idempotency_key="tvA-saga-001:provision_workspace:exec"
                ),
                verify=ActionSpec(
                    action="get_workspace",
                    args={"customer_id": "c123"}
                ),
                reversibility="full",
                criticality="high"
            )
        ]
    )
  
    await orchestrator.run_saga(saga_definition)

    # Test Vector B: Idempotent replay of reserve_username execute.
    tvb_payload = {
        "saga_id": "tvA-saga-001",
        "step_id": "reserve_username",
        "execute": {
            "action": "reserve_username",
            "args": {"customer_id": "c123", "username": "acme"},
            "idempotency_key": "tvA-saga-001:reserve_username:exec"
        }
    }
    tvb_response = await client.call_method(
        url="a2a://agent/identity",
        method="saga.step.execute",
        params=tvb_payload,
        headers=orchestrator._get_headers()
    )
    logger.info(f"Test Vector B replay response: {tvb_response}")

if __name__ == "__main__":
    asyncio.run(main())
