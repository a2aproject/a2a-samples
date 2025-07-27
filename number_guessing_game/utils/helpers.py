"""utils.helpers
Generic helper functions shared by the demo agents.
"""

from __future__ import annotations

import time
import uuid
import json
from typing import Any, Dict, Tuple, List

# ---------------------------------------------------------------------------
# Task-building helpers
# ---------------------------------------------------------------------------


def _create_completed_task_from_parts(
    parts: List[Dict[str, Any]],
    tasks: Dict[str, Any],
    *,
    context_id: str | None = None,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Create and register a *completed* Task containing *parts*."""

    task_id = str(uuid.uuid4())
    task = {
        "kind": "task",
        "id": task_id,
        "contextId": context_id or str(uuid.uuid4()),
        "status": {
            "state": "completed",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "artifacts": [
            {
                "artifactId": str(uuid.uuid4()),
                "name": "response",
                "description": "Agent response payload",
                "parts": parts,
            }
        ],
    }

    if metadata:
        task["metadata"] = metadata

    tasks[task_id] = task
    return task


# Public convenience wrapper -------------------------------------------------

def create_text_task(
    text: str,
    tasks: Dict[str, Any],
    *,
    context_id: str | None = None,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return a completed Task containing a single text part."""

    return _create_completed_task_from_parts(
        [{"kind": "text", "text": text}],
        tasks,
        context_id=context_id,
        metadata=metadata,
    )

# ---------------------------------------------------------------------------
# Small reusable utilities
# ---------------------------------------------------------------------------

def get_first_text_part(message: Dict[str, Any]) -> str | None:
    """Return trimmed text of the first part whose kind == "text"."""

    for part in message.get("parts", []):
        if part.get("kind") == "text":
            return part.get("text", "").strip()
    return None


def parse_int_in_range(text: str, low: int, high: int) -> int | None:
    """Parse *text* as int ensuring *low* ≤ value ≤ *high*, else ``None``."""

    try:
        value = int(text)
    except (ValueError, TypeError):
        return None
    return value if low <= value <= high else None


def safe_extract_plain_text(rpc_resp: Dict[str, Any]) -> str:
    """Extract the first text part from a completed Task; tolerate errors."""

    if not rpc_resp:
        return "No response"
    try:
        return rpc_resp["result"]["artifacts"][0]["parts"][0]["text"]
    except Exception:  # noqa: BLE001 – broad for robustness in demo
        return "Malformed response"


def try_parse_json(text: str) -> Tuple[bool, Any]:
    """Attempt ``json.loads`` returning *(success, value)* tuple instead of raising."""

    try:
        return True, json.loads(text)
    except json.JSONDecodeError:
        return False, None 