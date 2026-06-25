from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import Event, EventQueue
from timestamp_ext.core import TimestampExtension


def wrap_executor(executor: AgentExecutor, ext: TimestampExtension) -> AgentExecutor:
    """Wrap an executor in a decorator that automatically adds timestamps to messages and artifacts."""
    return _TimestampingAgentExecutor(delegate=executor, ext=ext)


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
            context, self._wrap_queue_if_requested(context=context, queue=event_queue)
        )

    def _wrap_queue_if_requested(
        self, context: RequestContext, queue: EventQueue
    ) -> EventQueue:
        if self._ext.is_requested(context):
            return _TimestampingEventQueue(delegate=queue, ext=self._ext)
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
