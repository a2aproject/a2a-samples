from collections.abc import AsyncIterator, Callable

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
from a2a.types import (
    AgentCard,
    CancelTaskRequest,
    DeleteTaskPushNotificationConfigRequest,
    GetExtendedAgentCardRequest,
    GetTaskPushNotificationConfigRequest,
    GetTaskRequest,
    ListTaskPushNotificationConfigsRequest,
    ListTaskPushNotificationConfigsResponse,
    ListTasksRequest,
    ListTasksResponse,
    SendMessageRequest,
    StreamResponse,
    SubscribeToTaskRequest,
    Task,
    TaskPushNotificationConfig,
)

from timestamp_ext.core import URI, TimestampExtension


_MESSAGING_METHODS = {'send_message', 'send_message_streaming'}


def wrap_client(client: Client, ext: TimestampExtension) -> Client:
    """Returns a Client that ensures all outgoing messages have timestamps."""
    return _TimestampingClient(delegate_client=client, ext=ext)


def wrap_client_factory(factory: ClientFactory, ext: TimestampExtension) -> ClientFactory:
    """Returns a ClientFactory that handles this extension."""
    return _TimestampingClientFactory(delegate_client_factory=factory, ext=ext)


def client_interceptor(ext: TimestampExtension) -> ClientCallInterceptor:
    """Get a client interceptor that requests this extension."""
    return _TimestampingClientInterceptor(ext=ext)


class _TimestampingClientFactory(ClientFactory):
    """A ClientFactory decorator to aid in adding timestamps.

    This factory determines if agents support the timestamp extension, and, if
    so, ensures that outgoing messages have timestamps.
    """

    def __init__(self, delegate_client_factory: ClientFactory, ext: TimestampExtension):
        self._delegate_client_factory = delegate_client_factory
        self._ext = ext

    def register(self, label: str, generator: TransportProducer) -> None:
        self._delegate_client_factory.register(label, generator)

    def create(
        self,
        card: AgentCard,
        interceptors: list[ClientCallInterceptor] | None = None,
    ) -> Client:
        interceptors = list(interceptors or [])
        interceptors.append(client_interceptor(ext=self._ext))
        return self._delegate_client_factory.create(card, interceptors)


class _TimestampingClient(Client):
    """A Client decorator that adds timestamps to outgoing messages."""

    def __init__(self, delegate_client: Client, ext: TimestampExtension):
        super().__init__()
        self._delegate_client = delegate_client
        self._ext = ext

    async def send_message(
        self,
        request: SendMessageRequest,
        *,
        context: ClientCallContext | None = None,
    ) -> AsyncIterator[StreamResponse]:
        self._ext.apply_timestamp(request.message)
        async for e in self._delegate_client.send_message(request, context=context):
            yield e

    async def get_task(
        self,
        request: GetTaskRequest,
        *,
        context: ClientCallContext | None = None,
    ) -> Task:
        return await self._delegate_client.get_task(request, context=context)

    async def list_tasks(
        self,
        request: ListTasksRequest,
        *,
        context: ClientCallContext | None = None,
    ) -> ListTasksResponse:
        return await self._delegate_client.list_tasks(request, context=context)

    async def cancel_task(
        self,
        request: CancelTaskRequest,
        *,
        context: ClientCallContext | None = None,
    ) -> Task:
        return await self._delegate_client.cancel_task(request, context=context)

    async def create_task_push_notification_config(
        self,
        request: TaskPushNotificationConfig,
        *,
        context: ClientCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        return await self._delegate_client.create_task_push_notification_config(
            request, context=context
        )

    async def get_task_push_notification_config(
        self,
        request: GetTaskPushNotificationConfigRequest,
        *,
        context: ClientCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        return await self._delegate_client.get_task_push_notification_config(
            request, context=context
        )

    async def list_task_push_notification_configs(
        self,
        request: ListTaskPushNotificationConfigsRequest,
        *,
        context: ClientCallContext | None = None,
    ) -> ListTaskPushNotificationConfigsResponse:
        return await self._delegate_client.list_task_push_notification_configs(
            request, context=context
        )

    async def delete_task_push_notification_config(
        self,
        request: DeleteTaskPushNotificationConfigRequest,
        *,
        context: ClientCallContext | None = None,
    ) -> None:
        return await self._delegate_client.delete_task_push_notification_config(
            request, context=context
        )

    async def subscribe(
        self,
        request: SubscribeToTaskRequest,
        *,
        context: ClientCallContext | None = None,
    ) -> AsyncIterator[StreamResponse]:
        async for e in self._delegate_client.subscribe(request, context=context):
            yield e

    async def get_extended_agent_card(
        self,
        request: GetExtendedAgentCardRequest,
        *,
        context: ClientCallContext | None = None,
        signature_verifier: Callable[[AgentCard], None] | None = None,
    ) -> AgentCard:
        return await self._delegate_client.get_extended_agent_card(
            request,
            context=context,
            signature_verifier=signature_verifier,
        )

    async def close(self) -> None:
        await self._delegate_client.close()


class _TimestampingClientInterceptor(ClientCallInterceptor):
    """A client interceptor that adds timestamps to outgoing messages.

    It also requests the timestamp extension via the A2A-Extensions header.
    """

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
        self._ext.apply_timestamp(args.input.message)
        # Request the extension via the A2A-Extensions header. Other
        # interceptors' extensions are preserved by with_a2a_extensions.
        if args.context is None:
            args.context = ClientCallContext()
        args.context.service_parameters = ServiceParametersFactory.create_from(
            args.context.service_parameters, [with_a2a_extensions([URI])]
        )

    async def after(self, args: AfterArgs) -> None:
        return None
