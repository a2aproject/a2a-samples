# ruff: noqa
"""Helpers for child-agent A2A message payloads."""

from typing import Any
from uuid import uuid4


def create_child_message_payload(
    query: str,
    context_id: str,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Build a child-agent message payload.

    A2A treats a present taskId as a resume of an existing task on the
    receiving server. New work must omit taskId so the child creates one.
    """
    message: dict[str, Any] = {
        'role': 'user',
        'parts': [{'kind': 'text', 'text': query}],
        'messageId': uuid4().hex,
        'contextId': context_id,
    }
    if task_id:
        message['taskId'] = task_id
    return {'message': message}


def child_task_id_from_result(result: object) -> str | None:
    """Return the child-local task id from a streaming result, if present."""
    event_task_id = getattr(result, 'task_id', None)
    if isinstance(event_task_id, str) and event_task_id:
        return event_task_id
    # Task objects expose id plus a status; request wrappers expose only id.
    result_id = getattr(result, 'id', None)
    if isinstance(result_id, str) and result_id and hasattr(result, 'status'):
        return result_id
    return None
