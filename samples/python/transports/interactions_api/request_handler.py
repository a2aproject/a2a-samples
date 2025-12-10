import logging

from collections.abc import AsyncGenerator

from a2a.client.transports import ClientTransport
from a2a.server.context import ServerCallContext
from a2a.server.events import Event
from a2a.server.request_handlers.request_handler import RequestHandler
from a2a.types import (
    DeleteTaskPushNotificationConfigParams,
    GetTaskPushNotificationConfigParams,
    ListTaskPushNotificationConfigParams,
    Message,
    MessageSendParams,
    Task,
    TaskIdParams,
    TaskPushNotificationConfig,
    TaskQueryParams,
)


logger = logging.getLogger(__name__)


class ClientTransportProxyRequestHandler(RequestHandler):
    """Request handler for all incoming requests to a ClientTransport.

    This handler forwards all incoming requests to a ClientTransport. This allows
    building a thin proxy over an existing transport, allowing that transport to
    be re-exported in other formats.
    """

    def __init__(
        self,
        transport: ClientTransport,
    ):
        self._transport = transport

    async def on_get_task(
        self,
        params: TaskQueryParams,
        context: ServerCallContext | None = None,
    ) -> Task | None:
        return await self._transport.get_task(params)

    async def on_cancel_task(
        self, params: TaskIdParams, context: ServerCallContext | None = None
    ) -> Task | None:
        return await self._transport.cancel_task(params)

    async def on_message_send(
        self,
        params: MessageSendParams,
        context: ServerCallContext | None = None,
    ) -> Message | Task:
        return await self._transport.send_message(params)

    async def on_message_send_stream(
        self,
        params: MessageSendParams,
        context: ServerCallContext | None = None,
    ) -> AsyncGenerator[Event]:
        async for event in self._transport.send_message_streaming(params):
            yield event

    async def on_resubscribe_to_task(
        self,
        params: TaskIdParams,
        context: ServerCallContext | None = None,
    ) -> AsyncGenerator[Event]:
        async for event in self._transport.resubscribe(params):
            yield event

    async def on_set_task_push_notification_config(
        self,
        params: TaskPushNotificationConfig,
        context: ServerCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        return await self._transport.set_task_callback(params)

    async def on_get_task_push_notification_config(
        self,
        params: TaskIdParams | GetTaskPushNotificationConfigParams,
        context: ServerCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        if isinstance(params, TaskIdParams):
            params = GetTaskPushNotificationConfigParams(id=params.id)
        return await self._transport.get_task_callback(params)

    async def on_list_task_push_notification_config(
        self,
        params: ListTaskPushNotificationConfigParams,
        context: ServerCallContext | None = None,
    ) -> list[TaskPushNotificationConfig]:
        raise NotImplementedError

    async def on_delete_task_push_notification_config(
        self,
        params: DeleteTaskPushNotificationConfigParams,
        context: ServerCallContext | None = None,
    ) -> None:
        raise NotImplementedError
