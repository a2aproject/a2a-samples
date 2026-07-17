"""End-to-end showcase for the timestamp extension.

This file is meant to be read top-to-bottom as a tutorial. It demonstrates
both sides of the timestamp extension:

* On the **server**, the agent's executor is wrapped with
  ``TimestampExtension.wrap_executor``. With that single line, every
  outgoing artifact and status-update message is automatically stamped
  with the current time (when the client requests the extension).

* On the **client**, the ``ClientFactory`` is wrapped with
  ``TimestampExtension.wrap_client_factory``. With that single line, the
  client advertises the extension via the ``A2A-Extensions`` header and
  exposes the timestamps the server attached.

The whole thing runs in-process: the Starlette app is driven by httpx's
``ASGITransport``, so there's no real socket and no fixture machinery to
maintain.

Run it standalone with::

    cd samples/python/extensions/timestamp
    uv sync --group dev
    uv run pytest -s -v

The ``-s`` flag is recommended; the showcase prints the events it sees so
you can read them in the test output.
"""

# ruff: noqa: S101  # `assert` is the standard pytest pattern.

import datetime

import httpx

from a2a.client.client import ClientConfig
from a2a.client.client_factory import ClientFactory
from a2a.helpers.proto_helpers import (
    new_task_from_user_message,
    new_text_artifact,
    new_text_message,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types.a2a_pb2 import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    Message,
    Part,
    Role,
    SendMessageRequest,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from a2a.utils.constants import TransportProtocol
from starlette.applications import Starlette
from timestamp_ext import TIMESTAMP_FIELD, TimestampExtension


_AGENT_URL = 'http://timestamp-ext-showcase.invalid'


# ---------------------------------------------------------------------------
# 1. The agent.
#
# A trivial executor that emits a task, a working status update with a
# message, an artifact, and a final completed status. None of this code
# knows or cares about the timestamp extension; the wrapper does the work.
# ---------------------------------------------------------------------------


class EchoExecutor(AgentExecutor):
    """Emits one artifact then completes."""

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        task = context.current_task or new_task_from_user_message(
            context.message
        )
        await event_queue.enqueue_event(task)
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(
                    state=TaskState.TASK_STATE_WORKING,
                    message=new_text_message('working...'),
                ),
            )
        )
        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                artifact=new_text_artifact(name='result', text='hello!'),
            )
        )
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(state=TaskState.TASK_STATE_COMPLETED),
            )
        )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# 2. The showcase.
# ---------------------------------------------------------------------------


async def test_timestamp_extension_round_trip():
    # Use a fixed clock so the showcase output is reproducible and we can
    # assert on the exact value at the end.
    fixed_ts = 1_700_000_000.0
    expected_iso = datetime.datetime.fromtimestamp(
        fixed_ts, datetime.UTC
    ).isoformat()
    ext = TimestampExtension(now_fn=lambda: fixed_ts)

    # ---- Server-side wiring -------------------------------------------------
    #
    # Two extension touch-points:
    #   * ``ext.add_to_card(card)`` advertises support on the agent card.
    #   * ``ext.wrap_executor(...)`` decorates the executor so emitted
    #     artifacts and status messages get timestamped automatically.
    #
    card = ext.add_to_card(
        AgentCard(
            name='Echo',
            description='echo agent that demonstrates the timestamp extension',
            version='1.0.0',
            default_input_modes=['text'],
            default_output_modes=['text'],
            capabilities=AgentCapabilities(streaming=True),
            supported_interfaces=[
                AgentInterface(
                    protocol_binding=TransportProtocol.JSONRPC,
                    url=_AGENT_URL,
                    protocol_version='1.0',
                )
            ],
        )
    )

    handler = DefaultRequestHandler(
        agent_executor=ext.wrap_executor(EchoExecutor()),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    app = Starlette(
        routes=[
            *create_agent_card_routes(card),
            *create_jsonrpc_routes(handler, rpc_url='/'),
        ]
    )

    # ---- Client-side wiring -------------------------------------------------
    #
    # The single extension touch-point on the client side is
    # ``ext.wrap_client_factory(...)`` below: the wrapper installs an
    # interceptor that sends the ``A2A-Extensions: <uri>`` header on every
    # send_message call.
    #
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url=_AGENT_URL
    ) as httpx_client:
        factory = ext.wrap_client_factory(
            ClientFactory(
                ClientConfig(httpx_client=httpx_client, streaming=True)
            )
        )
        client = factory.create(card)

        request = SendMessageRequest(
            message=Message(
                role=Role.ROLE_USER,
                parts=[Part(text='hi')],
                message_id='req-1',
            )
        )

        print('\n--- streaming response from the agent ---')
        artifacts: list = []
        status_messages: list = []
        async for chunk in client.send_message(request):
            kind = chunk.WhichOneof('payload')
            if chunk.HasField('artifact_update'):
                art = chunk.artifact_update.artifact
                artifacts.append(art)
                print(
                    f'  artifact "{art.name}" @ {art.metadata[TIMESTAMP_FIELD]}'
                )
            elif chunk.HasField('status_update'):
                status = chunk.status_update.status
                if status.HasField('message'):
                    msg = status.message
                    status_messages.append(msg)
                    print(
                        f'  status={TaskState.Name(status.state)} message '
                        f'@ {msg.metadata[TIMESTAMP_FIELD]}'
                    )
                else:
                    print(f'  status={TaskState.Name(status.state)}')
            else:
                print(f'  event of kind {kind}')

        await client.close()

    # ---- Confidence assertions ----------------------------------------------
    #
    # The showcase is also a regression test: every artifact and status
    # message that came back across the wire should carry the expected
    # timestamp, proving the round trip works.
    #
    assert artifacts, 'agent did not emit an artifact'
    assert status_messages, 'agent did not emit a status message'
    for art in artifacts:
        assert art.metadata[TIMESTAMP_FIELD] == expected_iso
    for msg in status_messages:
        assert msg.metadata[TIMESTAMP_FIELD] == expected_iso
