"""utils.protocol_wrappers
Helper functions that wrap A2A SDK types so agent code can stay focused on
business logic.
"""

from __future__ import annotations

import asyncio
import uuid

from a2a.client import ClientConfig, ClientFactory, minimal_agent_card
from a2a.client.client_task_manager import ClientTaskManager
from a2a.types import Message, Role, Task, TaskIdParams, TextPart
from a2a.utils.message import get_message_text


__all__ = [
    'cancel_task',
    'extract_text',
    'send_followup',
    'send_text',
    'send_text_async',
]


# ---------------------------------------------------------------------------
# Client helpers (Bob et al.)
# ---------------------------------------------------------------------------


_client_factory = ClientFactory(ClientConfig())


async def send_text_async(
    port: int,
    text: str,
    *,
    context_id: str | None = None,
    reference_task_ids: list[str] | None = None,
    task_id: str | None = None,
):
    """Send *text* to the target agent via the A2A ``message/send`` operation.

    Args:
        port: TCP port where the target agent is listening.
        text: Payload to send as a plain-text message.
        context_id: Optional conversation context ID to maintain multi-turn state.
        reference_task_ids: Optional list of task IDs this message replies to.
        task_id: Explicit task ID to reuse (follow-up scenarios).

    Returns:
        Union[Task, Message]: The final object produced by the agent—normally a
        ``Task`` but may be a plain ``Message`` for very small interactions.
    """
    client = _client_factory.create(
        minimal_agent_card(f'http://localhost:{port}/a2a/v1')
    )
    msg = Message(
        kind='message',
        role=Role.user,
        message_id=uuid.uuid4().hex,
        context_id=context_id,
        reference_task_ids=reference_task_ids or [],
        parts=[TextPart(text=text)],
        task_id=task_id,
    )

    task_manager = ClientTaskManager()
    last_message: Message | None = None

    async for event in client.send_message(msg):  # type: ignore[attr-defined]
        # Unwrap tuple from transport implementations
        if isinstance(event, tuple):
            event = event[0]
        # Let the SDK task manager handle state aggregation
        await task_manager.process(event)
        if isinstance(event, Message):
            last_message = event

    task = task_manager.get_task()
    if task:
        return task
    if last_message is not None:
        return last_message
    raise RuntimeError('No response from agent')


def send_text(
    port: int,
    text: str,
    *,
    context_id: str | None = None,
    reference_task_ids: list[str] | None = None,
    task_id: str | None = None,
):
    """Synchronous helper that delegates to :func:`send_text_async`.

    The helper transparently detects whether the caller is already running
    inside an event loop (e.g. inside a Jupyter notebook or another async
    framework) and chooses the appropriate execution strategy.

    Args:
        port: TCP port where the target agent is listening.
        text: Payload to send as a plain-text message.
        context_id: Optional conversation context ID.
        reference_task_ids: Optional list of task IDs this message replies to.
        task_id: Explicit task ID to reuse (follow-up scenarios).

    Returns:
        Union[Task, Message]: See :func:`send_text_async`.
    """
    try:
        return asyncio.run(
            send_text_async(
                port,
                text,
                context_id=context_id,
                reference_task_ids=reference_task_ids,
                task_id=task_id,
            )
        )
    except RuntimeError:
        # Fallback when called from within an existing running loop (e.g. Jupyter)
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.run_until_complete(
                send_text_async(
                    port,
                    text,
                    context_id=context_id,
                    reference_task_ids=reference_task_ids,
                    task_id=task_id,
                )
            )
        raise


def send_followup(
    port: int,
    resp_task: Task,
    text: str,
):
    """Convenience helper to send a *text* follow-up message that keeps the existing
    conversation context and task identifiers intact.

    Parameters
    ----------
    port
        Listening port of the target agent.
    resp_task
        The original Task to which we want to send a follow-up.
    text
        The plain-text content of the follow-up message.

    Returns:
    -------
    Task | Message
        The resulting SDK object returned by the agent (normally a Task).
    """
    return send_text(
        port,
        text,
        context_id=resp_task.context_id,
        reference_task_ids=[resp_task.id],
        task_id=resp_task.id,
    )


# ---------------------------------------------------------------------------
# cancel_task helper
# ---------------------------------------------------------------------------


async def _cancel_task_async(port: int, task_id: str) -> None:
    client = _client_factory.create(
        minimal_agent_card(f'http://localhost:{port}/a2a/v1')
    )
    await client.cancel_task(TaskIdParams(id=task_id))


def cancel_task(port: int, task_id: str) -> None:
    """Synchronously request cancellation of *task_id* on the remote agent.

    The wrapper executes :func:`_cancel_task_async` while handling the common
    case where the caller might already sit inside an event loop.

    Args:
        port: TCP port where the target agent is reachable.
        task_id: Identifier of the task to cancel.
    """
    try:
        asyncio.run(_cancel_task_async(port, task_id))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.run_until_complete(_cancel_task_async(port, task_id))
        else:
            raise


# ---------------------------------------------------------------------------
# Convenience extraction helpers
# ---------------------------------------------------------------------------


def extract_text(obj: Task | Message):
    """Return plain text from a Task or Message, using SDK helpers when possible."""
    if isinstance(obj, Message):
        return get_message_text(obj)

    if isinstance(obj, Task) and obj.artifacts:
        # Prefer the newest artifact/part (at the end) but fall back gracefully.
        for artifact in reversed(obj.artifacts):
            if artifact.parts:
                for part in reversed(artifact.parts):
                    if hasattr(part, 'root') and hasattr(part.root, 'text'):
                        return part.root.text  # type: ignore[attr-defined]
    return ''
