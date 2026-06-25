import datetime
import time

from collections.abc import Callable, Iterable

from a2a.extensions.common import find_extension_by_uri
from a2a.server.agent_execution import RequestContext
from a2a.server.events.event_queue import Event
from a2a.types.a2a_pb2 import (
    AgentCard,
    AgentExtension,
    Artifact,
    Message,
    Role,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)


_CORE_PATH = 'github.com/a2aproject/a2a-samples/extensions/timestamp/v1'
URI = f'https://{_CORE_PATH}'
TIMESTAMP_FIELD = f'{_CORE_PATH}/timestamp'


class TimestampExtension:
    """An implementation of the Timestamp extension."""

    def __init__(self, now_fn: Callable[[], float] | None = None):
        self._now_fn = now_fn or time.time
        self._agent_extension = AgentExtension(uri=URI, description='Adds timestamps to messages and artifacts.')

    def add_to_card(self, card: AgentCard) -> AgentCard:
        """Add this extension to an AgentCard."""
        card.capabilities.extensions.append(self._agent_extension)
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

    def apply_timestamp(self, o: Message | Artifact) -> None:
        """Add a timestamp to a message or artifact."""
        # Respect existing timestamps.
        if self.has_timestamp(o):
            return
        now = self._now_fn()
        dt = datetime.datetime.fromtimestamp(now, datetime.UTC)
        o.metadata[TIMESTAMP_FIELD] = dt.isoformat()

    def timestamp_event(self, event: Event) -> None:
        """Add a timestamp to a server-side event."""
        for o in self._get_messages_in_event(event):
            self.apply_timestamp(o)

    def has_timestamp(self, o: Message | Artifact) -> bool:
        """Returns whether a message or artifact has a timestamp."""
        return TIMESTAMP_FIELD in o.metadata

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
