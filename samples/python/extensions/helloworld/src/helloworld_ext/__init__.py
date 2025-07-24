import datetime
from collections.abc import Callable, Iterable
from typing import Any

from a2a.client import ClientCallInterceptor
from a2a.client.middleware import ClientCallContext
from a2a.extensions.common import HTTP_EXTENSION_HEADER, find_extension_by_uri
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types import (
    AgentCard,
    AgentExtension,
    Artifact,
    Message,
    Role,
    SendMessageRequest,
    SendStreamingMessageRequest,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)

_CORE_PATH = 'github.com/a2aproject/a2a-samples/extensions/helloworld/v1'
URI = f'https://{_CORE_PATH}'
TIMESTAMP_FIELD = f'{_CORE_PATH}/timestamp'


class HelloWorldExtension:
    """An implementation of the Helloworld extension."""

    def __init__(self, now_fn: Callable[[], float]):
        self._now_fn = now_fn

    # Option 1 for adding to a card: let the developer do it themselves.
    def agent_extension(self) -> AgentExtension:
        """Get the AgentExtension representing this extension."""
        return AgentExtension(
            uri=URI,
            description='Adds timestamps to messages and artifacts.',
        )

    # Option 2 for adding to a card: do it for them.
    def add_to_card(self, card: AgentCard) -> AgentCard:
        """Add this extension to an AgentCard."""
        if not (exts := card.capabilities.extensions):
            exts = card.capabilities.extensions = []
        exts.append(self.agent_extension())
        return card

    def is_supported(self, card: AgentCard | None) -> bool:
        """Returns whether this extension is supported by the AgentCard."""
        if card:
            return find_extension_by_uri(card, URI) is not None
        return False

    def activate(self, context: RequestContext) -> bool:
        if URI in context.requested_extensions:
            context.add_activated_extension(URI)
            return True
        return False

    # Option 1 for adding to a message: self-serve.
    def add_timestamp(self, o: Message | Artifact) -> None:
        """Add a timestamp to a message or artifact."""
        # Respect existing timestamps.
        if self.has_timestamp(o):
            return
        if o.metadata is None:
            o.metadata = {}
        now = self._now_fn()
        dt = datetime.datetime.fromtimestamp(now, datetime.UTC)
        o.metadata[TIMESTAMP_FIELD] = dt.isoformat()

    # Option 2: assisted, but still self-serve
    def add_if_activated(
        self, o: Message | Artifact, context: RequestContext
    ) -> None:
        if self.activate(context):
            self.add_timestamp(o)

    # Option 3 for servers: timestamp an event.
    def timestamp_event(
        self,
        event: Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent,
    ) -> None:
        for o in self._get_messages_in_event(event):
            self.add_timestamp(o)

    # Option 4: helper class
    def get_timestamper(self, context: RequestContext) -> 'MessageTimestamper':
        active = self.activate(context)
        return MessageTimestamper(active, self)

    def has_timestamp(self, o: Message | Artifact) -> bool:
        if o.metadata:
            return TIMESTAMP_FIELD in o.metadata
        return False

    # Option 5: Fully managed via a decorator. This is the most complicated, but
    # easiest for a developer to use.
    def wrap_executor(self, executor: AgentExecutor) -> AgentExecutor:
        """Wrap an executor in a decorator that automatically adds timestamps to messages and artifacts."""
        return _TimestampingAgentExecutor(executor, self)

    def request_activation_http(
        self, http_kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an http_kwargs to request activation of this extension."""
        if not (headers := http_kwargs['headers']):
            headers = http_kwargs['headers'] = {}
        header_val = URI
        if headers.get(HTTP_EXTENSION_HEADER):
            header_val = headers[HTTP_EXTENSION_HEADER] + ', ' + URI
        headers[HTTP_EXTENSION_HEADER] = header_val
        return http_kwargs

    # Option 2 for clients: timestamp your JSON RPC payloads.
    def timestamp_request_message(
        self, request: SendMessageRequest | SendStreamingMessageRequest
    ) -> None:
        """Add a timestamp to an outgoing request."""
        self.add_timestamp(request.params.message)

    # Option 3 for clients: use a client interceptor.
    def client_interceptor(self) -> ClientCallInterceptor:
        """Get a client interceptor that activates this extension."""
        return _TimestampingClientInterceptor(self)

    def _get_messages_in_event(
        self,
        event: Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent,
    ) -> Iterable[Message | Artifact]:
        if isinstance(event, TaskStatusUpdateEvent) and event.status.message:
            return [event.status.message]
        if isinstance(event, TaskArtifactUpdateEvent):
            return [event.artifact]
        if isinstance(event, Message):
            return [event]
        if isinstance(event, Task):
            return self._get_artifacts_and_messages_in_task(event)
        return []

    def _get_artifacts_and_messages_in_task(
        self, t: Task
    ) -> Iterable[Message | Artifact]:
        if t.artifacts:
            yield from t.artifacts
        if t.history:
            yield from (m for m in t.history if m.role == Role.agent)
        if t.status.message:
            yield t.status.message


class MessageTimestamper:
    def __init__(self, active: bool, ext: HelloWorldExtension):
        self._active = active
        self._ext = ext

    def timestamp(self, o: Message | Artifact) -> None:
        if self._active:
            self._ext.add_timestamp(o)


class _TimestampingAgentExecutor(AgentExecutor):
    def __init__(self, delegate: AgentExecutor, ext: HelloWorldExtension):
        self._delegate = delegate
        self._ext = ext

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        # Wrap the EventQueue so that all outgoing messages/status updates have
        # timestamps.
        return await self._delegate.execute(
            context, self._maybe_wrap_queue(context, event_queue)
        )

    def _maybe_wrap_queue(
        self, context: RequestContext, queue: EventQueue
    ) -> EventQueue:
        if self._ext.activate(context):
            return _TimestampingEventQueue(queue, self._ext)
        return queue

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        return await self._delegate.cancel(context, event_queue)


class _TimestampingEventQueue(EventQueue):
    """An EventQueue decorator that adds timestamps to all events."""

    def __init__(self, delegate: EventQueue, ext: HelloWorldExtension):
        self._delegate = delegate
        self._ext = ext

    async def enqueue_event(
        self,
        event: Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent,
    ) -> None:
        # If we're here, we're activated. Timestamp everything.
        self._ext.timestamp_event(event)
        return await self._delegate.enqueue_event(event)

    # Finish out all delegate methods.

    async def dequeue_event(
        self, no_wait: bool = False
    ) -> Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent:
        return await self._delegate.dequeue_event(no_wait)

    async def close(self) -> None:
        return await self._delegate.close()

    def tap(self) -> EventQueue:
        return self._delegate.tap()

    def is_closed(self) -> bool:
        return self._delegate.is_closed()

    def task_done(self) -> None:
        return self._delegate.task_done()


_MESSAGING_METHODS = {'message/send', 'message/stream'}


class _TimestampingClientInterceptor(ClientCallInterceptor):
    """A client interceptor that adds timestamps to outgoing messages."""

    def __init__(self, ext: HelloWorldExtension):
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
        body: SendMessageRequest | SendStreamingMessageRequest
        if method_name == 'message/send':
            body = SendMessageRequest.model_validate(request_payload)
        else:
            body = SendStreamingMessageRequest.model_validate(request_payload)
        self._ext.timestamp_request_message(body)
        # Request that we activate the extension, and timestamp the message.
        return (
            body.model_dump(),
            self._ext.request_activation_http(http_kwargs),
        )


__all__ = [
    'TIMESTAMP_FIELD',
    'URI',
    'HelloWorldExtension',
    'MessageTimestamper',
]
