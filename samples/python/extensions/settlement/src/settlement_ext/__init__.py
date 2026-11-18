"""An implementation of the Settlement extension.

This extension adds escrow-based payment to the A2A task lifecycle. Mirrors
the structure of the timestamp extension: a small extension class offering
support methods that range from fully manual (build and read metadata
yourself) to managed (an executor wrapper that verifies escrow before the
agent runs).

The release decision deliberately stays with the client. There is no
auto-release path: the client calls ``settle()`` (or ``release()`` /
``refund()``) once it has observed the terminal task state.
"""

import asyncio
import re
import time

from typing import Any

import httpx

from a2a.client.client import ClientCallContext
from a2a.client.interceptors import (
    AfterArgs,
    BeforeArgs,
    ClientCallInterceptor,
)
from a2a.client.service_parameters import (
    ServiceParametersFactory,
    with_a2a_extensions,
)
from a2a.extensions.common import find_extension_by_uri
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types.a2a_pb2 import (
    AgentCard,
    AgentExtension,
    Message,
    SendMessageRequest,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)


_CORE_PATH = 'github.com/a2aproject/a2a-samples/extensions/settlement/v1'
URI = f'https://{_CORE_PATH}'
ESCROW_ID_FIELD = f'{_CORE_PATH}/escrow_id'
AMOUNT_FIELD = f'{_CORE_PATH}/amount'
EXCHANGE_URL_FIELD = f'{_CORE_PATH}/exchange_url'

_MESSAGING_METHODS = {'send_message', 'send_message_streaming'}

# Escrow IDs arrive in message metadata and are untrusted input.
_ESCROW_ID_RE = re.compile(r'^[A-Za-z0-9_\-]{1,128}$')
_HTTP_NOT_FOUND = 404

# How long to remember seen escrow IDs for the reuse guard. Matches a
# typical exchange-side escrow TTL.
_SEEN_ESCROW_TTL_S = 30 * 60

_RELEASE_STATES = {TaskState.TASK_STATE_COMPLETED}
_REFUND_STATES = {
    TaskState.TASK_STATE_FAILED,
    TaskState.TASK_STATE_CANCELED,
    TaskState.TASK_STATE_REJECTED,
}


def _valid_escrow_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_ESCROW_ID_RE.fullmatch(value))


def _metadata_value(metadata: Any, field: str) -> Any | None:
    if field in metadata:
        return metadata[field]
    return None


class ExchangeClient:
    """Minimal async client for the settlement exchange interface.

    Covers the four endpoints the extension spec requires. Any conforming
    exchange implementation works; this class has no knowledge of a
    specific deployment.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip('/'),
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=30.0,
            transport=transport,
        )

    async def create_escrow(self, *, provider_id: str, amount: int) -> dict[str, Any]:
        resp = await self._client.post(
            '/exchange/escrow',
            json={'provider_id': provider_id, 'amount': amount},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_escrow(self, escrow_id: str) -> dict[str, Any] | None:
        resp = await self._client.get(f'/exchange/escrows/{escrow_id}')
        if resp.status_code == _HTTP_NOT_FOUND:
            return None
        resp.raise_for_status()
        return resp.json()

    async def release_escrow(self, escrow_id: str) -> dict[str, Any]:
        resp = await self._client.post('/exchange/release', json={'escrow_id': escrow_id})
        resp.raise_for_status()
        return resp.json()

    async def refund_escrow(self, escrow_id: str) -> dict[str, Any]:
        resp = await self._client.post('/exchange/refund', json={'escrow_id': escrow_id})
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()


class SettlementExtension:
    """An implementation of the Settlement extension.

    Args:
        exchange: Client for the settlement exchange this agent uses.
        account_id: This agent's account ID on the exchange. Used by the
            executor wrapper to confirm incoming escrows actually name
            this agent as the provider.
    """

    def __init__(self, exchange: ExchangeClient, account_id: str):
        self._exchange = exchange
        self._account_id = account_id

    # Option 1 for adding to a card: let the developer do it themselves.
    def agent_extension(self) -> AgentExtension:
        """Get the AgentExtension representing this extension."""
        return AgentExtension(
            uri=URI,
            description='Accepts escrow-based payment via a settlement exchange.',
        )

    # Option 2 for adding to a card: do it for them.
    def add_to_card(self, card: AgentCard) -> AgentCard:
        """Add this extension to an AgentCard."""
        card.capabilities.extensions.append(self.agent_extension())
        return card

    def is_supported(self, card: AgentCard | None) -> bool:
        """Returns whether this extension is supported by the AgentCard."""
        if card:
            return find_extension_by_uri(card, URI) is not None
        return False

    def is_requested(self, context: RequestContext) -> bool:
        """Returns whether the client requested this extension for the call."""
        return URI in context.requested_extensions

    # Client side, manual: build the metadata yourself.
    def add_escrow_metadata(
        self,
        message: Message,
        *,
        escrow_id: str,
        amount: int,
        exchange_url: str,
    ) -> None:
        """Attach settlement metadata fields to an outgoing message."""
        message.metadata[ESCROW_ID_FIELD] = escrow_id
        message.metadata[AMOUNT_FIELD] = amount
        message.metadata[EXCHANGE_URL_FIELD] = exchange_url

    @staticmethod
    def read_escrow_metadata(message: Message) -> dict[str, Any] | None:
        """Read settlement metadata fields from a message, if present."""
        metadata = message.metadata
        if ESCROW_ID_FIELD not in metadata:
            return None
        return {
            'escrow_id': metadata[ESCROW_ID_FIELD],
            'amount': _metadata_value(metadata, AMOUNT_FIELD),
            'exchange_url': _metadata_value(metadata, EXCHANGE_URL_FIELD),
        }

    # Client side: settle based on the terminal task state.
    async def settle(self, state: int, escrow_id: str) -> dict[str, Any] | None:
        """Release or refund an escrow for a terminal task state.

        Returns the exchange response, or None when the state is not
        terminal (no action taken).
        """
        if state in _RELEASE_STATES:
            return await self._exchange.release_escrow(escrow_id)
        if state in _REFUND_STATES:
            return await self._exchange.refund_escrow(escrow_id)
        return None

    async def release(self, escrow_id: str) -> dict[str, Any]:
        """Release an escrow (pay the provider)."""
        return await self._exchange.release_escrow(escrow_id)

    async def refund(self, escrow_id: str) -> dict[str, Any]:
        """Refund an escrow (return funds to the requester)."""
        return await self._exchange.refund_escrow(escrow_id)

    # Client side: an interceptor that activates the extension when the
    # agent supports it.
    def client_interceptor(self) -> ClientCallInterceptor:
        """Get a client interceptor that requests this extension."""
        return _SettlementClientInterceptor(self)

    # Server side: managed via a decorator. Verifies escrow before the
    # wrapped executor runs.
    def wrap_executor(
        self, executor: AgentExecutor, *, settlement_required: bool = False
    ) -> AgentExecutor:
        """Wrap an executor to verify escrow before execution.

        When the extension is requested and the incoming message carries an
        escrow ID, the wrapper confirms on the exchange that the escrow
        exists, is held, names this agent as provider, and matches the
        declared amount. Tasks failing verification are rejected before the
        delegate executor runs.

        Args:
            executor: The real executor to delegate to.
            settlement_required: If True, requests that activate the
                extension without settlement metadata are rejected. Default
                False (unpaid requests run normally).
        """
        return _SettledAgentExecutor(executor, self, settlement_required)

    async def verify_escrow(self, escrow_id: str, expected_amount: Any) -> str | None:
        """Check an escrow on the exchange. Returns a rejection reason or None."""
        escrow = await self._exchange.get_escrow(escrow_id)
        if escrow is None:
            return 'escrow not found'
        if escrow.get('status') != 'held':
            return f'escrow status is {escrow.get("status")!r}, expected held'
        if escrow.get('provider_id') != self._account_id:
            return 'escrow names a different provider'
        if expected_amount is not None and escrow.get('amount') != expected_amount:
            return 'escrow amount does not match message metadata'
        return None


class _SettledAgentExecutor(AgentExecutor):
    """Verifies escrow before delegating to the wrapped executor."""

    def __init__(
        self,
        delegate: AgentExecutor,
        ext: SettlementExtension,
        settlement_required: bool,
    ):
        self._delegate = delegate
        self._ext = ext
        self._settlement_required = settlement_required
        # Reuse guard: escrow IDs seen recently, with bounded growth.
        self._seen_escrows: dict[str, float] = {}
        self._seen_lock = asyncio.Lock()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        if self._ext.is_requested(context):
            reason = await self._check(context)
            if reason:
                await self._reject(context, event_queue, reason)
                return
        await self._delegate.execute(context, event_queue)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        return await self._delegate.cancel(context, event_queue)

    async def _check(self, context: RequestContext) -> str | None:
        """Returns a rejection reason, or None when execution may proceed."""
        message = context.message
        metadata = (
            SettlementExtension.read_escrow_metadata(message) if message is not None else None
        )
        if metadata is None:
            if self._settlement_required:
                return 'settlement required but no escrow metadata provided'
            return None

        escrow_id = metadata['escrow_id']
        if not _valid_escrow_id(escrow_id):
            return 'malformed escrow ID'

        async with self._seen_lock:
            self._prune_seen()
            if escrow_id in self._seen_escrows:
                return 'escrow already used for another task'
            self._seen_escrows[escrow_id] = time.monotonic()

        return await self._ext.verify_escrow(escrow_id, metadata['amount'])

    def _prune_seen(self) -> None:
        cutoff = time.monotonic() - _SEEN_ESCROW_TTL_S
        for escrow_id in [k for k, ts in self._seen_escrows.items() if ts < cutoff]:
            self._seen_escrows.pop(escrow_id, None)

    async def _reject(self, context: RequestContext, event_queue: EventQueue, reason: str) -> None:
        event = TaskStatusUpdateEvent(
            task_id=context.task_id,
            context_id=context.context_id,
            status=TaskStatus(state=TaskState.TASK_STATE_REJECTED),
        )
        event.metadata[f'{_CORE_PATH}/rejection_reason'] = reason
        await event_queue.enqueue_event(event)


class _SettlementClientInterceptor(ClientCallInterceptor):
    """Requests the settlement extension via the A2A-Extensions header
    whenever the target agent supports it and the outgoing message carries
    escrow metadata."""

    def __init__(self, ext: SettlementExtension):
        self._ext = ext

    async def before(self, args: BeforeArgs) -> None:
        if (
            not self._ext.is_supported(args.agent_card)
            or args.method not in _MESSAGING_METHODS
            or not isinstance(args.input, SendMessageRequest)
            or ESCROW_ID_FIELD not in args.input.message.metadata
        ):
            return
        if args.context is None:
            args.context = ClientCallContext()
        args.context.service_parameters = ServiceParametersFactory.create_from(
            args.context.service_parameters, [with_a2a_extensions([URI])]
        )

    async def after(self, args: AfterArgs) -> None:
        return None


__all__ = [
    'AMOUNT_FIELD',
    'ESCROW_ID_FIELD',
    'EXCHANGE_URL_FIELD',
    'URI',
    'ExchangeClient',
    'SettlementExtension',
]
