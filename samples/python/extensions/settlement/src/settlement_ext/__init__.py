"""A2A Settlement Extension — escrow-based payment for A2A agents.

Provides SettlementExtension with multiple integration levels:

  Option 1 (manual): use the helpers to build metadata and call the SDK yourself.
  Option 2 (server-side wrap): wrap_executor auto-verifies escrow before execution.
  Option 3 (client-side wrap): wrap_client auto-creates escrow before sending
            and auto-settles (release/refund) when the task reaches a terminal state.
"""

from __future__ import annotations

import asyncio
import logging
import time

from typing import TYPE_CHECKING, Any

from a2a.client import Client, ClientCallInterceptor, ClientEvent
from a2a.extensions.common import find_extension_by_uri
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.types import (
    AgentCard,
    AgentExtension,
    GetTaskPushNotificationConfigParams,
    Message,
    Task,
    TaskIdParams,
    TaskPushNotificationConfig,
    TaskQueryParams,
    TaskStatusUpdateEvent,
)
from a2a_settlement import SettlementExchangeClient
from a2a_settlement.agentcard import build_settlement_extension
from a2a_settlement.lifecycle import settle_for_task_state
from a2a_settlement.metadata import (
    build_settlement_metadata,
    get_settlement_block,
)


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from a2a.client.middleware import ClientCallContext
    from a2a.server.events.event_queue import EventQueue

logger = logging.getLogger(__name__)

URI = 'https://a2a-settlement.org/extensions/settlement/v1'
METADATA_KEY = 'a2a-se'

_TERMINAL_RELEASE = {'completed', 'TASK_STATE_COMPLETED'}
_TERMINAL_REFUND = {
    'failed',
    'canceled',
    'rejected',
    'TASK_STATE_FAILED',
    'TASK_STATE_CANCELED',
    'TASK_STATE_REJECTED',
}
_MESSAGING_METHODS = {'message/send', 'message/stream'}


class SettlementExtension:
    """A2A Settlement Extension implementation.

    Mirrors the pattern of the timestamp extension, offering multiple
    integration levels from fully manual to fully managed.

    Attributes:
        auto_verify: If True, the executor wrapper rejects tasks whose
            escrow cannot be verified on the exchange.
        auto_settle: If True, the client wrapper releases/refunds escrow
            automatically when a task reaches a terminal state.
        settlement_required: If True, the executor wrapper rejects tasks
            that activate settlement but do not include settlement
            metadata. Default False (freemium — unpaid requests allowed).

    Args:
        exchange_url: Base URL of the settlement exchange.
        api_key: Bearer token for the exchange.
        account_id: This agent's account ID on the exchange.
        auto_verify: If True, the executor wrapper rejects tasks whose
            escrow cannot be verified on the exchange. Default True.
        auto_settle: If True, the client wrapper releases/refunds escrow
            automatically when a task reaches a terminal state.
            Default True.
    """

    def __init__(
        self,
        exchange_url: str,
        api_key: str,
        account_id: str,
        *,
        auto_verify: bool = True,
        auto_settle: bool = True,
    ) -> None:
        self._exchange_url = exchange_url
        self._api_key = api_key
        self.account_id = account_id
        self.auto_verify = auto_verify
        self.auto_settle = auto_settle
        self.settlement_required = False
        self.exchange_client = SettlementExchangeClient(
            base_url=exchange_url,
            api_key=api_key,
        )

    # ── AgentCard integration ──────────────────────────────────

    def agent_extension(
        self,
        pricing: dict[str, Any] | None = None,
        *,
        required: bool = False,
    ) -> AgentExtension:
        """Build the AgentExtension object for this extension."""
        ext_dict = build_settlement_extension(
            exchange_urls=[self._exchange_url],
            account_ids={self._exchange_url: self.account_id},
            pricing=pricing,
            required=required,
        )
        return AgentExtension(**ext_dict)

    def add_to_card(
        self,
        card: AgentCard,
        pricing: dict[str, Any] | None = None,
        *,
        required: bool = False,
    ) -> AgentCard:
        """Add the settlement extension to an AgentCard."""
        if not card.capabilities.extensions:
            card.capabilities.extensions = []
        card.capabilities.extensions.append(
            self.agent_extension(pricing, required=required)
        )
        return card

    def is_supported(self, card: AgentCard | None) -> bool:
        """Check whether an AgentCard advertises settlement."""
        if card:
            return find_extension_by_uri(card, URI) is not None
        return False

    # ── Extension activation ───────────────────────────────────

    def activate(self, context: RequestContext) -> bool:
        """Activate the extension if the client requested it."""
        if URI in context.requested_extensions:
            context.add_activated_extension(URI)
            return True
        return False

    # ── Manual helpers (Option 1) ──────────────────────────────

    def create_escrow(
        self,
        *,
        provider_id: str,
        amount: int,
        task_id: str | None = None,
        task_type: str | None = None,
        ttl_minutes: int | None = None,
    ) -> dict[str, Any]:
        """Create an escrow on the exchange."""
        return self.exchange_client.create_escrow(
            provider_id=provider_id,
            amount=amount,
            task_id=task_id,
            task_type=task_type,
            ttl_minutes=ttl_minutes,
        )

    def release(self, escrow_id: str) -> dict[str, Any]:
        """Release an escrow (pay the provider)."""
        return self.exchange_client.release_escrow(escrow_id=escrow_id)

    def refund(
        self,
        escrow_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Refund an escrow (return tokens to requester)."""
        return self.exchange_client.refund_escrow(
            escrow_id=escrow_id, reason=reason
        )

    def verify_escrow(self, escrow_id: str) -> dict[str, Any] | None:
        """Look up an escrow on the exchange.

        Returns:
            The escrow dict, or None if the lookup fails.
        """
        try:
            return self.exchange_client.get_escrow(escrow_id=escrow_id)
        except (OSError, ValueError, KeyError):
            logger.warning(
                'Failed to verify escrow %s',
                escrow_id,
                exc_info=True,
            )
            return None

    def build_metadata(self, escrow: dict[str, Any]) -> dict[str, Any]:
        """Build the a2a-se metadata block from an escrow."""
        meta = build_settlement_metadata(
            escrow_id=escrow['escrow_id'],
            amount=escrow['amount'],
            fee_amount=escrow.get('fee_amount', 0),
            exchange_url=self._exchange_url,
            expires_at=escrow.get('expires_at', ''),
        )
        if not escrow.get('expires_at'):
            meta['a2a-se'].pop('expiresAt', None)
        return meta

    @staticmethod
    def read_metadata(
        message: Message | Task | dict,
    ) -> dict[str, Any] | None:
        """Extract the a2a-se block from a message or task."""
        return get_settlement_block(message)

    # ── Server-side: executor wrapper (Option 2) ───────────────

    def wrap_executor(self, executor: AgentExecutor) -> AgentExecutor:
        """Wrap an executor to verify escrow before execution.

        If the settlement extension is activated and the incoming
        message contains an escrowId, the wrapper verifies the
        escrow exists and is in 'held' status on the exchange
        before delegating to the real executor. If verification
        fails, the task is rejected.
        """
        return _SettledAgentExecutor(executor, self)

    # ── Client-side: client wrapper (Option 3) ─────────────────

    def wrap_client(self, client: Client) -> Client:
        """Wrap a client to auto-manage escrow lifecycle.

        Outgoing messages get escrow metadata injected. When the
        task reaches a terminal state, escrow is released or
        refunded.
        """
        return _SettledClient(client, self)

    def client_interceptor(self) -> ClientCallInterceptor:
        """Get a client interceptor that activates settlement."""
        return _SettlementClientInterceptor(self)


# ── Server-side wrapper ────────────────────────────────────────


class _SettledAgentExecutor(AgentExecutor):
    """Verifies escrow before delegating to the wrapped executor."""

    def __init__(
        self,
        delegate: AgentExecutor,
        ext: SettlementExtension,
    ) -> None:
        self._delegate = delegate
        self._ext = ext
        self._used_escrows: set[str] = set()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        if self._ext.activate(context) and self._ext.auto_verify:
            se_block = self._extract_settlement(context)
            reject = False
            if se_block and not await self._verify(se_block):
                reject = True
            elif not se_block and self._ext.settlement_required:
                logger.warning('Settlement required but no metadata provided')
                reject = True

            if reject:
                await event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        taskId=context.task_id or '',
                        contextId=context.context_id or '',
                        final=True,
                        status=TaskStatusUpdateEvent.Status(
                            state='failed',
                            message=Message(
                                messageId='settlement-reject',
                                role='agent',
                                parts=[],
                            ),
                        ),
                    )
                )
                return
        await self._delegate.execute(context, event_queue)

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        await self._delegate.cancel(context, event_queue)

    def _extract_settlement(self, context: RequestContext) -> dict | None:
        msg = context.message
        if msg and msg.metadata:
            return msg.metadata.get(METADATA_KEY)
        return None

    async def _verify(self, se_block: dict) -> bool:
        escrow_id = se_block.get('escrowId')
        if not escrow_id or escrow_id in self._used_escrows:
            if escrow_id:
                logger.warning('Escrow %s already used', escrow_id)
            return False
        escrow = await asyncio.to_thread(self._ext.verify_escrow, escrow_id)
        if not escrow:
            return False

        reason = self._check_escrow(se_block, escrow, escrow_id)
        if reason:
            logger.warning('Escrow %s rejected: %s', escrow_id, reason)
            return False
        self._used_escrows.add(escrow_id)
        return True

    def _check_escrow(
        self, se_block: dict, escrow: dict, escrow_id: str
    ) -> str | None:
        if escrow.get('provider_id') != self._ext.account_id:
            return (
                f'provider mismatch: expected {self._ext.account_id}, '
                f'got {escrow.get("provider_id")}'
            )
        expected_amount = se_block.get('amount')
        if (
            expected_amount is not None
            and escrow.get('amount') != expected_amount
        ):
            return (
                f'amount mismatch: expected {expected_amount}, '
                f'got {escrow.get("amount")}'
            )
        if escrow.get('status') != 'held':
            return f'unexpected status: {escrow.get("status")}'
        return None


# ── Client-side wrapper ────────────────────────────────────────


_ESCROW_TTL_S = 30 * 60  # 30 minutes, matches default exchange escrow TTL


class _SettledClient(Client):
    """Manages escrow around task messages.

    Keeps a mapping of task_id to escrow_id so it can settle
    automatically when the task reaches a terminal state.  Entries
    are pruned after ``_ESCROW_TTL_S`` to bound memory growth.
    """

    def __init__(self, delegate: Client, ext: SettlementExtension) -> None:
        self._delegate = delegate
        self._ext = ext
        self._escrows: dict[str, tuple[str, float]] = {}

    async def send_message(
        self,
        request: Message,
        *,
        context: ClientCallContext | None = None,
    ) -> AsyncIterator[ClientEvent | Message]:
        se_block = self._ext.read_metadata(request)
        escrow_id = se_block.get('escrowId') if se_block else None
        tracked = False

        async for event in self._delegate.send_message(
            request, context=context
        ):
            yield event
            if escrow_id and not tracked:
                task_id, _ = self._extract_task_state(event)
                if task_id:
                    self.track_escrow(task_id, escrow_id)
                    tracked = True
            if self._ext.auto_settle:
                await self._try_settle(event)

    async def get_task(
        self,
        request: TaskQueryParams,
        *,
        context: ClientCallContext | None = None,
    ) -> Task:
        task = await self._delegate.get_task(request, context=context)
        if self._ext.auto_settle:
            await self._try_settle(task)
        return task

    async def cancel_task(
        self,
        request: TaskIdParams,
        *,
        context: ClientCallContext | None = None,
    ) -> Task:
        task = await self._delegate.cancel_task(request, context=context)
        if self._ext.auto_settle:
            await self._try_settle(task)
        return task

    async def set_task_callback(
        self,
        request: TaskPushNotificationConfig,
        *,
        context: ClientCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        return await self._delegate.set_task_callback(request, context=context)

    async def get_task_callback(
        self,
        request: GetTaskPushNotificationConfigParams,
        *,
        context: ClientCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        return await self._delegate.get_task_callback(request, context=context)

    async def resubscribe(
        self,
        request: TaskIdParams,
        *,
        context: ClientCallContext | None = None,
    ) -> AsyncIterator[ClientEvent]:
        async for event in self._delegate.resubscribe(request, context=context):
            yield event
            if self._ext.auto_settle:
                await self._try_settle(event)

    async def get_card(
        self,
        *,
        context: ClientCallContext | None = None,
    ) -> AgentCard:
        return await self._delegate.get_card(context=context)

    def track_escrow(self, task_id: str, escrow_id: str) -> None:
        """Register an escrow for auto-settlement."""
        self._prune_stale()
        self._escrows[task_id] = (escrow_id, time.monotonic())

    def _prune_stale(self) -> None:
        cutoff = time.monotonic() - _ESCROW_TTL_S
        stale = [k for k, (_, ts) in self._escrows.items() if ts < cutoff]
        for k in stale:
            self._escrows.pop(k, None)

    async def _try_settle(self, event: Any) -> None:
        task_id, state = self._extract_task_state(event)
        if not task_id or not state:
            return

        entry = self._escrows.get(task_id)
        if not entry:
            return
        escrow_id = entry[0]

        try:
            await asyncio.to_thread(
                settle_for_task_state,
                self._ext.exchange_client,
                task_state=state,
                escrow_id=escrow_id,
            )
        except (OSError, ValueError, KeyError):
            logger.warning(
                'Auto-settle failed for escrow %s',
                escrow_id,
                exc_info=True,
            )
            return

        if state in _TERMINAL_RELEASE | _TERMINAL_REFUND:
            self._escrows.pop(task_id, None)

    @staticmethod
    def _extract_task_state(
        event: Any,
    ) -> tuple[str | None, str | None]:
        if isinstance(event, Task):
            return (
                event.id,
                event.status.state if event.status else None,
            )
        if isinstance(event, TaskStatusUpdateEvent):
            return (
                event.taskId,
                event.status.state if event.status else None,
            )
        return None, None


class _SettlementClientInterceptor(ClientCallInterceptor):
    """Activates the settlement extension on outgoing requests."""

    def __init__(self, ext: SettlementExtension) -> None:
        self._ext = ext

    async def intercept(
        self,
        method_name: str,
        request_payload: dict[str, Any],
        http_kwargs: dict[str, Any],
        agent_card: AgentCard | None,
        context: ClientCallContext | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if (
            not self._ext.is_supported(agent_card)
            or method_name not in _MESSAGING_METHODS
        ):
            return (request_payload, http_kwargs)

        headers = http_kwargs.setdefault('headers', {})
        header_key = 'A2A-Extensions'
        existing = headers.get(header_key, '')
        if URI not in existing:
            headers[header_key] = f'{existing}, {URI}'.lstrip(', ')

        return (request_payload, http_kwargs)


__all__ = [
    'METADATA_KEY',
    'URI',
    'SettlementExtension',
]
