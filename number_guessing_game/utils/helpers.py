"""utils.helpers
Generic helper functions still shared by the demo agents.

Utility functions shared by the demo agents.
"""

from __future__ import annotations

import json

from typing import Any


# ---------------------------------------------------------------------------
# Small reusable utilities
# ---------------------------------------------------------------------------


def parse_int_in_range(text: str, low: int, high: int) -> int | None:
    """Return an integer parsed from *text* that lies within the inclusive range.

    Args:
        text: Input string that should represent an integer.
        low: Lower inclusive bound.
        high: Upper inclusive bound.

    Returns:
        The parsed integer if it is within the range ``[low, high]``;
        otherwise ``None`` when the input is not an integer or outside the
        bounds.
    """
    try:
        value = int(text)
    except (ValueError, TypeError):
        return None
    return value if low <= value <= high else None


def try_parse_json(text: str) -> tuple[bool, Any]:
    """Attempt to parse *text* as JSON.

    Args:
        text: Raw string to be parsed.

    Returns:
        Tuple[bool, Any]: A pair where the first element is a boolean flag
        indicating whether parsing succeeded, and the second element is the
        parsed Python object when successful or ``None`` otherwise.
    """
    try:
        return True, json.loads(text)
    except json.JSONDecodeError:
        return False, None
