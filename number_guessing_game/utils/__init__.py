"""utils package

Public re-exports for convenience when importing from the *utils* package.
Only the symbols listed in ``__all__`` are exposed to callers, avoiding
namespace pollution while still offering an ergonomic façade.
"""

# Transport helpers ---------------------------------------------------------
from .transport import JSONRPC_VERSION, build_handler  # noqa: F401

# Agent card helpers --------------------------------------------------------
from .card import make_agent_card, build_complete_agent_card  # noqa: F401

# Generic helpers -----------------------------------------------------------
from .helpers import (
    create_text_task,
    get_first_text_part,
    parse_int_in_range,
    safe_extract_plain_text,
    try_parse_json,
)  # noqa: F401

# Agent façade --------------------------------------------------------------
from .agent import ToyA2AAgent, run_agent_forever  # noqa: F401

__all__ = [
    # transport
    "JSONRPC_VERSION",
    "build_handler",
    # card
    "make_agent_card",
    "build_complete_agent_card",
    # helpers
    "create_text_task",
    "get_first_text_part",
    "parse_int_in_range",
    "safe_extract_plain_text",
    "try_parse_json",
    # agent
    "ToyA2AAgent",
    "run_agent_forever",
] 