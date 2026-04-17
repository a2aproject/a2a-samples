import datetime
import time

from collections.abc import AsyncIterator, Callable, Iterable
from typing import Any

from a2a.client import (
    Client,
    ClientCallInterceptor,
    ClientFactory,
)
from a2a.client.client import ClientCallContext
from a2a.client.client_factory import TransportProducer
from a2a.client.interceptors import AfterArgs, BeforeArgs
from a2a.client.service_parameters import (
    ServiceParametersFactory,
    with_a2a_extensions,
)
from a2a.extensions.common import find_extension_by_uri
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import Event, EventQueue
from a2a.types.a2a_pb2 import (
    AgentCard,
    AgentExtension,
    Artifact,
    CancelTaskRequest,
    DeleteTaskPushNotificationConfigRequest,
    GetExtendedAgentCardRequest,
    GetTaskPushNotificationConfigRequest,
    GetTaskRequest,
    ListTaskPushNotificationConfigsRequest,
    ListTaskPushNotificationConfigsResponse,
    ListTasksRequest,
    ListTasksResponse,
    Message,
    Role,
    SendMessageRequest,
    StreamResponse,
    SubscribeToTaskRequest,
    Task,
    TaskArtifactUpdateEvent,
    TaskPushNotificationConfig,
    TaskStatusUpdateEvent,
)


_CORE_PATH = 'github.com/a2aproject/a2a-samples/extensions/timestamp/v1'
URI = f'https://{_CORE_PATH}'
TIMESTAMP_FIELD = f'{_CORE_PATH}/timestamp'


class TimestampExtension:
    """An implementation of the Timestamp extension.

    This extension implementation illustrates several ways for an extension to
    provide functionality to agent developers. In general, the support methods
    range from totally hands off, where all responsibility for using the
    extension correctly is left to the developer, to totally hands-on, where
    the developer sets up strategic decorators for core classes which then
    manage implementing the extension logic. Each of the methods have comments
    indicating the level of support they provide.
    """

    def __init__(self, now_fn: Callable[[], float] | None = None):
        self._now_fn = now_fn or time.time

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
        card.capabilities.extensions.append(self.agent_extension())
        return card

    def is_supported(self, card: AgentCard | None) -> bool:
        """Returns whether this extension is supported by the AgentCard."""
        if card:
            return find_extension_by_uri(card, URI) is not None
        return False

    def is_requested(self, context: RequestContext) -> bool:
        """Returns whether the client requested this extension for the call.

        The extension is considered requested if the caller indicated it in
        an A2A-Extensions header.
        """
        return URI in context.requested_extensions

    # Option 1 for adding to a message: self-serve.
    def add_timestamp(self, o: Message | Artifact) -> None:
        """Add a timestamp to a message or artifact."""
        # Respect existing timestamps.
        if self.has_timestamp(o):
            return
        now = self._now_fn()
        dt = datetime.datetime.fromtimestamp(now, datetime.UTC)
        o.metadata[TIMESTAMP_FIELD] = dt.isoformat()

    # Option 2: assisted, but still self-serve
    def add_if_requested(
        self, o: Message | Artifact, context: RequestContext
    ) -> None:
        """Add a timestamp to a message or artifact if the extension is requested."""
        if self.is_requested(context):
            self.add_timestamp(o)

    # Option 3 for servers: timestamp an event.
    def timestamp_event(self, event: Event) -> None:
        """Add a timestamp to a server-side event."""
        for o in self._get_messages_in_event(event):
            self.add_timestamp(o)

    # Option 4: helper class
    def get_timestamper(self, context: RequestContext) -> 'MessageTimestamper':
        """Returns a helper class for adding timestamps to messages/artifacts.

        This detects whether the extension should be applied based on the
        current RequestContext. If not, timestamps are not added.
        """
        return MessageTimestamper(self.is_requested(context), self)

    def get_timestamp(self, o: Message | Artifact) -> datetime.datetime | None:
        """Get a timestamp from a message or artifact."""
        if self.has_timestamp(o):
            return datetime.datetime.fromisoformat(o.metadata[TIMESTAMP_FIELD])
        return None

    def has_timestamp(self, o: Message | Artifact) -> bool:
        """Returns whether a message or artifact has a timestamp."""
        return TIMESTAMP_FIELD in o.metadata

    # Option 5: Fully managed via a decorator. This is the most complicated, but
    # easiest for a developer to use.
    def wrap_executor(self, executor: AgentExecutor) -> AgentExecutor:
        """Wrap an executor in a decorator that automatically adds timestamps to messages and artifacts."""
        return _TimestampingAgentExecutor(executor, self)

    def request_extension_http(
        self, http_kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an http_kwargs to request this extension."""
        http_kwargs['headers'] = ServiceParametersFactory.create_from(
            http_kwargs.get('headers'), [with_a2a_extensions([URI])]
        )
        return http_kwargs

    # Option 2 for clients: timestamp your outgoing requests.
    # Option 1 is to self-serve add the timestamp to your message.
    def timestamp_request_message(self, request: SendMessageRequest) -> None:
        """Add a timestamp to an outgoing request."""
        self.add_timestamp(request.message)

    # Option 3 for clients: use a client interceptor.
    def client_interceptor(self) -> ClientCallInterceptor:
        """Get a client interceptor that requests this extension."""
        return _TimestampingClientInterceptor(self)

    # Option 4 for clients: wrap the client itself.
    def wrap_client(self, client: Client) -> Client:
        """Returns a Client that ensures all outgoing messages have timestamps."""
        return _TimestampingClient(client, self)

    # Option 5 for clients: an extension-aware client factory.
    def wrap_client_factory(self, factory: ClientFactory) -> ClientFactory:
        """Returns a ClientFactory that handles this extension."""
        return _TimestampClientFactory(factory, self)

    def _get_messages_in_event(
        self, event: Event
    ) -> Iterable[Message | Artifact]:
        if isinstance(event, TaskStatusUpdateEvent) and event.status.HasField(
            'message'
        ):
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
        yield from t.artifacts
        yield from (m for m in t.history if m.role == Role.ROLE_AGENT)
        if t.status.HasField('message'):
            yield t.status.message


class MessageTimestamper:
    """Helper to add compliant timestamps to messages and artifacts.

    Timestamps are only added if the extension was requested by the client."""

    def __init__(self, active: bool, ext: TimestampExtension):
        self._active = active
        self._ext = ext

    def timestamp(self, o: Message | Artifact) -> None:
        """Add a timestamp to a message or artifact, if active."""
        if self._active:
            self._ext.add_timestamp(o)


class _TimestampingAgentExecutor(AgentExecutor):
    def __init__(self, delegate: AgentExecutor, ext: TimestampExtension):
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
        if self._ext.is_requested(context):
            return _TimestampingEventQueue(queue, self._ext)
        return queue

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        return await self._delegate.cancel(context, event_queue)


class _TimestampingEventQueue(EventQueue):
    """An EventQueue decorator that adds timestamps to all events."""

    def __init__(self, delegate: EventQueue, ext: TimestampExtension):
        self._delegate = delegate
        self._ext = ext

    async def enqueue_event(self, event: Event) -> None:
        # If we're here, the extension was requested. Timestamp everything.
        self._ext.timestamp_event(event)
        return await self._delegate.enqueue_event(event)


_MESSAGING_METHODS = {'send_message', 'send_message_streaming'}


class _TimestampClientFactory(ClientFactory):
    """A ClientFactory decorator to aid in adding timestamps.

    This factory determines if agents support the timestamp extension, and, if
    so, ensures that outgoing messages have timestamps.
    """

    def __init__(self, delegate: ClientFactory, ext: TimestampExtension):
        self._delegate = delegate
        self._ext = ext

    def register(self, label: str, generator: TransportProducer) -> None:
        self._delegate.register(label, generator)

    def create(
        self,
        card: AgentCard,
        interceptors: list[ClientCallInterceptor] | None = None,
    ) -> Client:
        interceptors = list(interceptors or [])
        interceptors.append(self._ext.client_interceptor())
        return self._delegate.create(card, interceptors)


class _TimestampingClient(Client):
    """A Client decorator that adds timestamps to outgoing messages."""

    def __init__(self, delegate: Client, ext: TimestampExtension):
        super().__init__()
        self._delegate = delegate
        self._ext = ext

    async def send_message(
        self,
        request: SendMessageRequest,
        *,
        context: ClientCallContext | None = None,
    ) -> AsyncIterator[StreamResponse]:
        self._ext.add_timestamp(request.message)
        async for e in self._delegate.send_message(request, context=context):
            yield e

    async def get_task(
        self,
        request: GetTaskRequest,
        *,
        context: ClientCallContext | None = None,
    ) -> Task:
        return await self._delegate.get_task(request, context=context)

    async def list_tasks(
        self,
        request: ListTasksRequest,
        *,
        context: ClientCallContext | None = None,
    ) -> ListTasksResponse:
        return await self._delegate.list_tasks(request, context=context)

    async def cancel_task(
        self,
        request: CancelTaskRequest,
        *,
        context: ClientCallContext | None = None,
    ) -> Task:
        return await self._delegate.cancel_task(request, context=context)

    async def create_task_push_notification_config(
        self,
        request: TaskPushNotificationConfig,
        *,
        context: ClientCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        return await self._delegate.create_task_push_notification_config(
            request, context=context
        )

    async def get_task_push_notification_config(
        self,
        request: GetTaskPushNotificationConfigRequest,
        *,
        context: ClientCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        return await self._delegate.get_task_push_notification_config(
            request, context=context
        )

    async def list_task_push_notification_configs(
        self,
        request: ListTaskPushNotificationConfigsRequest,
        *,
        context: ClientCallContext | None = None,
    ) -> ListTaskPushNotificationConfigsResponse:
        return await self._delegate.list_task_push_notification_configs(
            request, context=context
        )

    async def delete_task_push_notification_config(
        self,
        request: DeleteTaskPushNotificationConfigRequest,
        *,
        context: ClientCallContext | None = None,
    ) -> None:
        return await self._delegate.delete_task_push_notification_config(
            request, context=context
        )

    async def subscribe(
        self,
        request: SubscribeToTaskRequest,
        *,
        context: ClientCallContext | None = None,
    ) -> AsyncIterator[StreamResponse]:
        async for e in self._delegate.subscribe(request, context=context):
            yield e

    async def get_extended_agent_card(
        self,
        request: GetExtendedAgentCardRequest,
        *,
        context: ClientCallContext | None = None,
        signature_verifier: Callable[[AgentCard], None] | None = None,
    ) -> AgentCard:
        return await self._delegate.get_extended_agent_card(
            request,
            context=context,
            signature_verifier=signature_verifier,
        )

    async def close(self) -> None:
        await self._delegate.close()


class _TimestampingClientInterceptor(ClientCallInterceptor):
    """A client interceptor that adds timestamps to outgoing messages and
    requests the timestamp extension via the A2A-Extensions header."""

    def __init__(self, ext: TimestampExtension):
        self._ext = ext

    async def before(self, args: BeforeArgs) -> None:
        if (
            not self._ext.is_supported(args.agent_card)
            or args.method not in _MESSAGING_METHODS
            or not isinstance(args.input, SendMessageRequest)
        ):
            return
        # Timestamp the outgoing message.
        self._ext.timestamp_request_message(args.input)
        # Request the extension via the A2A-Extensions header. Other
        # interceptors' extensions are preserved by with_a2a_extensions.
        if args.context is None:
            args.context = ClientCallContext()
        args.context.service_parameters = ServiceParametersFactory.create_from(
            args.context.service_parameters, [with_a2a_extensions([URI])]
        )

    async def after(self, args: AfterArgs) -> None:
        return None


__all__ = [
    'TIMESTAMP_FIELD',
    'URI',
    'MessageTimestamper',
    'TimestampExtension',
]
