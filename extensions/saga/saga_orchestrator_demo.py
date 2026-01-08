"""Demo implementation of the A2A-SAGA extension orchestrator.

This module provides a demonstration of the Saga Orchestrator pattern
as specified in the A2A-SAGA RFC for multi-agent workflow management.
"""

import asyncio
import json
import logging

from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# --- Configuration & Constants ---
SAGA_EXTENSION_URI = 'https://a2a.dev/extensions/saga/v1'
A2A_EXTENSION_HEADER_KEY = 'A2A-Extensions'

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SagaOrchestrator')


# --- Mock Response Lookup Table ---
_MOCK_RESPONSES: dict[tuple[str, str], dict] = {
    ('reserve_username', 'saga.step.execute'): {
        'status': 'succeeded',
        'evidence': {'reservation_id': 'resv-001'}
    },
    ('create_customer_record', 'saga.step.execute'): {
        'status': 'succeeded',
        'evidence': {'customer_row_id': 'crm-777'}
    },
    ('provision_workspace', 'saga.step.verify'): {
        'status': 'not_verified',
        'details': {'workspace': None}
    },
    ('reserve_username', 'saga.step.compensate'): {
        'status': 'compensated',
        'evidence': {'released': True}
    },
    ('create_customer_record', 'saga.step.compensate'): {
        'status': 'compensated',
        'evidence': {'deleted': True}
    },
}


def _make_default_response() -> dict:
    """Create the default success response."""
    return {'status': 'succeeded', 'evidence': {}}


def _make_provision_response(idempotency_key: str | None) -> dict:
    """Create the provision_workspace execute response based on retry state."""
    if idempotency_key and idempotency_key.endswith(':retry-1'):
        return {
            'status': 'failed',
            'failure': {
                'failure_class': 'deterministic',
                'reason': 'Plan not available'
            }
        }
    return {
        'status': 'unknown',
        'failure': {
            'failure_class': 'unknown',
            'reason': 'timeout after dispatch'
        }
    }


# --- Mocks for A2A SDK (Replace with actual imports in production) ---
class A2AClient:
    """Mock client simulating JSON-RPC calls to remote agents.

    In a real implementation, this would be `a2a.Client`.
    """

    async def call_method(
        self,
        url: str,
        method: str,
        params: dict,
        headers: dict
    ) -> dict:
        """Simulates the network call.

        Replace this with actual HTTP/JSON-RPC transport logic.
        """
        logger.info('--> OUTBOUND RPC: %s to %s', method, url)
        logger.debug('    Params: %s', json.dumps(params))
        logger.debug('    Headers: %s', json.dumps(headers))

        # SIMULATION LOGIC FOR TEST VECTOR A + B (RFC Appendix B)
        idempotency_key = self._extract_idempotency_key(method, params)

        if idempotency_key in getattr(self, '_idempotency_store', {}):
            return self._idempotency_store[idempotency_key]

        step_id = params.get('step_id', '')
        response = self._get_mock_response(step_id, method, idempotency_key)

        if idempotency_key:
            self._store_response(idempotency_key, response)

        return response

    def _extract_idempotency_key(self, method: str, params: dict) -> str | None:
        """Extract the idempotency key from params based on method."""
        if method == 'saga.step.execute':
            return params.get('execute', {}).get('idempotency_key')
        if method == 'saga.step.compensate':
            return params.get('compensate', {}).get('idempotency_key')
        return None

    def _get_mock_response(
        self,
        step_id: str,
        method: str,
        idempotency_key: str | None
    ) -> dict:
        """Get the mock response for the given step and method."""
        key = (step_id, method)
        if key in _MOCK_RESPONSES:
            return _MOCK_RESPONSES[key].copy()

        if key == ('provision_workspace', 'saga.step.execute'):
            return _make_provision_response(idempotency_key)

        return _make_default_response()

    def _store_response(self, idempotency_key: str, response: dict) -> None:
        """Store the response for idempotency."""
        if not hasattr(self, '_idempotency_store'):
            self._idempotency_store = {}
        self._idempotency_store[idempotency_key] = response


# --- Data Structures ---
@dataclass(frozen=True)
class ActionSpec:
    """Specification for an action to be executed."""
    action: str
    args: dict[str, Any]


@dataclass(frozen=True)
class ExecuteSpec(ActionSpec):
    """Specification for executing an action with idempotency."""
    idempotency_key: str


@dataclass(frozen=True)
class CompensateSpec(ActionSpec):
    """Specification for compensating an action with idempotency."""
    idempotency_key: str


@dataclass(frozen=True)
class StepDefinition:
    """Definition of a single step in a saga."""
    step_id: str
    participant: str
    execute: ExecuteSpec
    reversibility: str
    criticality: str
    group: str | None = None
    verify: ActionSpec | None = None
    compensate: CompensateSpec | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class SagaDefinition:
    """Definition of a complete saga with all its steps."""
    saga_id: str
    goal: str
    steps: list[StepDefinition]
    policy: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class SagaContext:
    """Runtime context for a saga execution."""
    saga_id: str
    applied_steps_by_group: OrderedDict[str, list[StepDefinition]] = field(
        default_factory=OrderedDict
    )
    retry_counts: dict[str, int] = field(default_factory=dict)


class StepResult(Enum):
    """Enumeration of possible step result statuses."""
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    UNKNOWN = 'unknown'


class SagaFailedError(Exception):
    """Custom exception for saga failures."""


# --- The Orchestrator Implementation ---
class SagaOrchestrator:
    """Orchestrator for executing sagas across multiple agents."""

    def __init__(self, client: A2AClient) -> None:
        """Initialize the orchestrator with an A2A client."""
        self.client = client

    def _get_headers(self) -> dict[str, str]:
        """Normative Requirement: 5.1 Header Negotiation."""
        return {
            'Content-Type': 'application/json',
            A2A_EXTENSION_HEADER_KEY: SAGA_EXTENSION_URI
        }

    async def run_saga(self, saga_def: SagaDefinition) -> dict:
        """Main entry point for executing a saga."""
        saga_id = saga_def.saga_id
        steps = saga_def.steps
        ctx = SagaContext(saga_id=saga_id)

        logger.info('Starting Saga %s', saga_id)

        # 1. Group steps by 'group' ID for parallel execution
        # Logic: Sequential groups, parallel steps within groups.
        grouped_steps = self._group_steps(steps)
        ctx.applied_steps_by_group = OrderedDict(
            (gid, []) for gid in grouped_steps
        )

        try:
            for group_id, group_steps in grouped_steps.items():
                logger.info(
                    'Executing Group: %s (%d steps)',
                    group_id,
                    len(group_steps)
                )

                # Execute group in parallel (O1 Conformance)
                results = await asyncio.gather(*[
                    self._execute_step(ctx, step, group_id) for step in group_steps
                ])

                # Check for failures in the group
                failed_results = [
                    r for r in results if r['status'] != StepResult.SUCCEEDED.value
                ]

                if failed_results:
                    self._handle_group_failure(group_id, failed_results)

        except SagaFailedError as e:
            logger.warning('Aborting Saga: %s', e)
            await self._compensate_saga(ctx)
            return {'status': 'compensated', 'error': str(e)}

        logger.info('Saga %s Completed Successfully!', saga_id)
        return {'status': 'completed', 'ctx': ctx}

    def _handle_group_failure(
        self,
        group_id: str,
        failed_results: list[dict]
    ) -> None:
        """Handle saga failure for a group."""
        logger.error(
            'Group %s failed. Initiating Compensation.',
            group_id
        )
        raise SagaFailedError(
            'Saga Failed at group %s: %s', group_id, failed_results[0]
        )

    def _group_steps(
        self, steps: list[StepDefinition]
    ) -> dict[str, list[StepDefinition]]:
        """Helper to preserve order of groups but allow parallel steps within."""
        groups: dict[str, list[StepDefinition]] = OrderedDict()
        for step in steps:
            g_id = step.group or f'default_{step.step_id}'
            if g_id not in groups:
                groups[g_id] = []
            groups[g_id].append(step)
        return groups

    async def _execute_step(
        self, ctx: SagaContext, step: StepDefinition, group_id: str
    ) -> dict:
        """Executes a single step, handling Idempotency, Headers, and Unknown outcomes."""
        step_id = step.step_id

        # Normative Requirement: 9.1 Idempotency Keys
        if not step.execute.idempotency_key:
            raise ValueError(
                'Missing execute.idempotency_key for step %s', step_id
            )

        payload = {
            'saga_id': ctx.saga_id,
            'step_id': step_id,
            'execute': {
                'action': step.execute.action,
                'args': step.execute.args,
                'idempotency_key': step.execute.idempotency_key
            }
        }

        # RPC Call
        response = await self.client.call_method(
            url=step.participant,
            method='saga.step.execute',
            params=payload,
            headers=self._get_headers()
        )

        status = response.get('status')

        # Normative Requirement: 8.2 Verify Unknown Outcomes
        if status == StepResult.UNKNOWN.value and step.verify is not None:
            logger.info('Step %s returned UNKNOWN. Verifying...', step_id)
            verification = await self._verify_step(ctx, step)
            if verification['status'] == 'verified':
                status = StepResult.SUCCEEDED.value
            elif verification['status'] == 'not_verified':
                logger.info(
                    'Verification failed for %s. Retrying execute once.',
                    step_id
                )
                response = await self._retry_execute_step(ctx, step)
                status = response.get('status')

        if status in (
            StepResult.FAILED.value,
            StepResult.UNKNOWN.value,
            'pending_approval'
        ):
            response.setdefault('failure', {
                'failure_class': 'unknown',
                'reason': 'unspecified failure'
            })

        # Record success for potential future compensation
        if status == StepResult.SUCCEEDED.value:
            ctx.applied_steps_by_group[group_id].append(step)

        return {'step_id': step_id, 'status': status, 'raw': response}

    async def _verify_step(
        self, ctx: SagaContext, step: StepDefinition
    ) -> dict:
        """Verifies the outcome of a step."""
        if step.verify is None:
            raise ValueError(
                'Missing verify action for step %s', step.step_id
            )

        payload = {
            'saga_id': ctx.saga_id,
            'step_id': step.step_id,
            'verify': {
                'action': step.verify.action,
                'args': step.verify.args
            }
        }
        return await self.client.call_method(
            url=step.participant,
            method='saga.step.verify',
            params=payload,
            headers=self._get_headers()
        )

    async def _retry_execute_step(
        self, ctx: SagaContext, step: StepDefinition
    ) -> dict:
        """Retries a step execution with a new idempotency key."""
        step_id = step.step_id
        retry_count = ctx.retry_counts.get(step_id, 0) + 1
        ctx.retry_counts[step_id] = retry_count

        retry_payload = {
            'saga_id': ctx.saga_id,
            'step_id': step_id,
            'execute': {
                'action': step.execute.action,
                'args': step.execute.args,
                'idempotency_key': f'{step.execute.idempotency_key}:retry-{retry_count}'
            }
        }

        return await self.client.call_method(
            url=step.participant,
            method='saga.step.execute',
            params=retry_payload,
            headers=self._get_headers()
        )

    async def _compensate_saga(self, ctx: SagaContext) -> None:
        """Normative Requirement: 7.3 Compensation Ordering.

        Executes compensation in Reverse Order (LIFO).
        """
        logger.info('--- STARTING COMPENSATION PHASE ---')

        # Reverse group order; parallel within a group.
        for group_id in reversed(list(ctx.applied_steps_by_group)):
            group_steps = ctx.applied_steps_by_group[group_id]
            if not group_steps:
                continue
            await asyncio.gather(*[
                self._compensate_step(ctx, step) for step in group_steps
            ])

        logger.info('--- COMPENSATION COMPLETE ---')

    async def _compensate_step(
        self, ctx: SagaContext, step: StepDefinition
    ) -> None:
        """Compensates a single step."""
        if step.compensate is None:
            logger.warning(
                'Skipping step %s (No compensation defined)', step.step_id
            )
            return

        step_id = step.step_id
        if not step.compensate.idempotency_key:
            raise ValueError(
                'Missing compensate.idempotency_key for step %s', step_id
            )

        payload = {
            'saga_id': ctx.saga_id,
            'step_id': step_id,
            'compensate': {
                'action': step.compensate.action,
                'args': step.compensate.args,
                'idempotency_key': step.compensate.idempotency_key
            }
        }

        logger.info('Compensating %s...', step_id)
        await self.client.call_method(
            url=step.participant,
            method='saga.step.compensate',
            params=payload,
            headers=self._get_headers()
        )


# --- Test Vector Runner ---
async def main() -> None:
    """Runs the saga test vectors from the RFC."""
    client = A2AClient()
    orchestrator = SagaOrchestrator(client)

    # Define the Saga from Test Vector A (Appendix B.2)
    saga_definition = SagaDefinition(
        saga_id='tvA-saga-001',
        goal='Onboard customer c123',
        steps=[
            # Group 1: Parallel
            StepDefinition(
                step_id='reserve_username',
                group='g1',
                participant='a2a://agent/identity',
                execute=ExecuteSpec(
                    action='reserve_username',
                    args={'customer_id': 'c123', 'username': 'acme'},
                    idempotency_key='tvA-saga-001:reserve_username:exec'
                ),
                compensate=CompensateSpec(
                    action='release_username',
                    args={'username': 'acme'},
                    idempotency_key='tvA-saga-001:reserve_username:comp'
                ),
                verify=ActionSpec(
                    action='get_reservation',
                    args={'username': 'acme'}
                ),
                reversibility='full',
                criticality='medium'
            ),
            StepDefinition(
                step_id='create_customer_record',
                group='g1',
                participant='a2a://agent/crm',
                execute=ExecuteSpec(
                    action='create_customer',
                    args={'customer_id': 'c123', 'name': 'ACME'},
                    idempotency_key='tvA-saga-001:create_customer_record:exec'
                ),
                compensate=CompensateSpec(
                    action='delete_customer',
                    args={'customer_id': 'c123'},
                    idempotency_key='tvA-saga-001:create_customer_record:comp'
                ),
                reversibility='full',
                criticality='high'
            ),
            # Group 2: Dependent (Will Fail)
            StepDefinition(
                step_id='provision_workspace',
                group='g2',
                participant='a2a://agent/provision',
                execute=ExecuteSpec(
                    action='provision_workspace',
                    args={'customer_id': 'c123', 'plan': 'pro'},
                    idempotency_key='tvA-saga-001:provision_workspace:exec'
                ),
                verify=ActionSpec(
                    action='get_workspace',
                    args={'customer_id': 'c123'}
                ),
                reversibility='full',
                criticality='high'
            )
        ]
    )

    await orchestrator.run_saga(saga_definition)

    # Test Vector B: Idempotent replay of reserve_username execute.
    tvb_payload = {
        'saga_id': 'tvA-saga-001',
        'step_id': 'reserve_username',
        'execute': {
            'action': 'reserve_username',
            'args': {'customer_id': 'c123', 'username': 'acme'},
            'idempotency_key': 'tvA-saga-001:reserve_username:exec'
        }
    }
    tvb_response = await client.call_method(
        url='a2a://agent/identity',
        method='saga.step.execute',
        params=tvb_payload,
        headers=orchestrator._get_headers()  # noqa: SLF001
    )
    logger.info('Test Vector B replay response: %s', tvb_response)


if __name__ == '__main__':
    asyncio.run(main())
