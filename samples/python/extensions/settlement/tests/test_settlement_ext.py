"""Tests for the settlement extension.

The exchange is faked with an in-process httpx MockTransport, so the tests
exercise the real request/response path of ExchangeClient without a network.
"""

# ruff: noqa: PLR0911, PLR2004, S101
# `assert` and literal values keep this tutorial-style test readable.

import json

import httpx
import pytest

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.context import ServerCallContext
from a2a.server.events.event_queue import EventQueue
from a2a.types.a2a_pb2 import (
    Message,
    Role,
    SendMessageRequest,
    TaskState,
)
from settlement_ext import (
    AMOUNT_FIELD,
    ESCROW_ID_FIELD,
    URI,
    ExchangeClient,
    SettlementExtension,
)


PROVIDER_ID = 'provider-1'


class FakeExchange:
    """In-memory exchange behind an httpx MockTransport."""

    def __init__(self):
        self.escrows: dict[str, dict] = {}
        self.calls: list[str] = []
        self._next = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(f'{request.method} {request.url.path}')
        if request.method == 'POST' and request.url.path.endswith('/exchange/escrow'):
            body = json.loads(request.content)
            self._next += 1
            escrow_id = f'esc-{self._next}'
            escrow = {
                'escrow_id': escrow_id,
                'provider_id': body['provider_id'],
                'amount': body['amount'],
                'status': 'held',
            }
            self.escrows[escrow_id] = escrow
            return httpx.Response(200, json=escrow)
        if request.method == 'GET' and '/exchange/escrows/' in request.url.path:
            escrow_id = request.url.path.rsplit('/', 1)[-1]
            escrow = self.escrows.get(escrow_id)
            if escrow is None:
                return httpx.Response(404, json={'detail': 'not found'})
            return httpx.Response(200, json=escrow)
        if request.method == 'POST' and request.url.path.endswith(
            ('/exchange/release', '/exchange/refund')
        ):
            body = json.loads(request.content)
            escrow = self.escrows.get(body['escrow_id'])
            if escrow is None:
                return httpx.Response(404, json={'detail': 'not found'})
            if escrow['status'] != 'held':
                return httpx.Response(400, json={'detail': f'already {escrow["status"]}'})
            escrow['status'] = 'released' if request.url.path.endswith('/release') else 'refunded'
            return httpx.Response(200, json=escrow)
        return httpx.Response(404)


@pytest.fixture
def fake_exchange():
    return FakeExchange()


@pytest.fixture
def exchange_client(fake_exchange):
    return ExchangeClient(
        'https://exchange.test.invalid/api/v1',
        'key',
        transport=httpx.MockTransport(fake_exchange.handler),
    )


@pytest.fixture
def ext(exchange_client):
    return SettlementExtension(exchange_client, account_id=PROVIDER_ID)


class RecordingExecutor(AgentExecutor):
    """Records whether execute was called."""

    def __init__(self):
        self.executed = False

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        self.executed = True

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError


def _message_with_escrow(escrow_id: str, amount: int) -> Message:
    message = Message(message_id='msg-1', role=Role.ROLE_USER)
    message.metadata[ESCROW_ID_FIELD] = escrow_id
    message.metadata[AMOUNT_FIELD] = amount
    return message


def _context(message: Message | None, requested: bool) -> RequestContext:
    call_context = ServerCallContext(requested_extensions={URI} if requested else set())
    request = SendMessageRequest(message=message) if message is not None else None
    return RequestContext(
        call_context,
        request=request,
        task_id='task-1',
        context_id='ctx-1',
    )


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------


def test_metadata_roundtrip(ext):
    message = Message(message_id='m1', role=Role.ROLE_USER)
    ext.add_escrow_metadata(
        message,
        escrow_id='esc-42',
        amount=10,
        exchange_url='https://exchange.test.invalid/api/v1',
    )
    block = SettlementExtension.read_escrow_metadata(message)
    assert block is not None
    assert block['escrow_id'] == 'esc-42'
    assert block['amount'] == 10


def test_read_metadata_absent(ext):
    message = Message(message_id='m1', role=Role.ROLE_USER)
    assert SettlementExtension.read_escrow_metadata(message) is None


# ---------------------------------------------------------------------------
# Settle mapping
# ---------------------------------------------------------------------------


async def test_settle_releases_on_completed(ext, exchange_client, fake_exchange):
    escrow = await exchange_client.create_escrow(provider_id=PROVIDER_ID, amount=10)
    result = await ext.settle(TaskState.TASK_STATE_COMPLETED, escrow['escrow_id'])
    assert result['status'] == 'released'


async def test_settle_refunds_on_failed(ext, exchange_client):
    escrow = await exchange_client.create_escrow(provider_id=PROVIDER_ID, amount=10)
    result = await ext.settle(TaskState.TASK_STATE_FAILED, escrow['escrow_id'])
    assert result['status'] == 'refunded'


async def test_settle_no_action_on_working(ext):
    assert await ext.settle(TaskState.TASK_STATE_WORKING, 'esc-x') is None


async def test_second_release_rejected(ext, exchange_client):
    escrow = await exchange_client.create_escrow(provider_id=PROVIDER_ID, amount=10)
    await ext.release(escrow['escrow_id'])
    with pytest.raises(httpx.HTTPStatusError):
        await ext.release(escrow['escrow_id'])


# ---------------------------------------------------------------------------
# Executor wrapper
# ---------------------------------------------------------------------------


async def test_executor_runs_with_valid_escrow(ext, exchange_client):
    escrow = await exchange_client.create_escrow(provider_id=PROVIDER_ID, amount=10)
    delegate = RecordingExecutor()
    wrapped = ext.wrap_executor(delegate)
    message = _message_with_escrow(escrow['escrow_id'], 10)
    await wrapped.execute(_context(message, requested=True), EventQueue())
    assert delegate.executed


async def test_executor_rejects_unknown_escrow(ext):
    delegate = RecordingExecutor()
    wrapped = ext.wrap_executor(delegate)
    message = _message_with_escrow('esc-unknown', 10)
    queue = EventQueue()
    await wrapped.execute(_context(message, requested=True), queue)
    assert not delegate.executed
    event = await queue.dequeue_event()
    assert event.status.state == TaskState.TASK_STATE_REJECTED


async def test_executor_rejects_amount_mismatch(ext, exchange_client):
    escrow = await exchange_client.create_escrow(provider_id=PROVIDER_ID, amount=10)
    delegate = RecordingExecutor()
    wrapped = ext.wrap_executor(delegate)
    # Client claims 99 in metadata; escrow on the exchange holds 10.
    message = _message_with_escrow(escrow['escrow_id'], 99)
    await wrapped.execute(_context(message, requested=True), EventQueue())
    assert not delegate.executed


async def test_executor_rejects_wrong_provider(exchange_client):
    other_agent = SettlementExtension(exchange_client, account_id='someone-else')
    escrow = await exchange_client.create_escrow(provider_id=PROVIDER_ID, amount=10)
    delegate = RecordingExecutor()
    wrapped = other_agent.wrap_executor(delegate)
    message = _message_with_escrow(escrow['escrow_id'], 10)
    await wrapped.execute(_context(message, requested=True), EventQueue())
    assert not delegate.executed


async def test_executor_rejects_escrow_reuse(ext, exchange_client):
    escrow = await exchange_client.create_escrow(provider_id=PROVIDER_ID, amount=10)
    delegate = RecordingExecutor()
    wrapped = ext.wrap_executor(delegate)
    message = _message_with_escrow(escrow['escrow_id'], 10)
    await wrapped.execute(_context(message, requested=True), EventQueue())
    assert delegate.executed

    delegate.executed = False
    await wrapped.execute(_context(message, requested=True), EventQueue())
    assert not delegate.executed


async def test_executor_rejects_malformed_escrow_id(ext):
    delegate = RecordingExecutor()
    wrapped = ext.wrap_executor(delegate)
    message = _message_with_escrow('../../etc/passwd', 10)
    await wrapped.execute(_context(message, requested=True), EventQueue())
    assert not delegate.executed


async def test_unpaid_request_runs_when_not_required(ext):
    delegate = RecordingExecutor()
    wrapped = ext.wrap_executor(delegate)
    message = Message(message_id='m1', role=Role.ROLE_USER)
    await wrapped.execute(_context(message, requested=True), EventQueue())
    assert delegate.executed


async def test_unpaid_request_rejected_when_required(ext):
    delegate = RecordingExecutor()
    wrapped = ext.wrap_executor(delegate, settlement_required=True)
    message = Message(message_id='m1', role=Role.ROLE_USER)
    await wrapped.execute(_context(message, requested=True), EventQueue())
    assert not delegate.executed


async def test_extension_not_requested_skips_verification(ext):
    delegate = RecordingExecutor()
    wrapped = ext.wrap_executor(delegate)
    message = _message_with_escrow('esc-unknown', 10)
    await wrapped.execute(_context(message, requested=False), EventQueue())
    assert delegate.executed
