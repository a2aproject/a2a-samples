"""agent_Carol.py
AgentCarol – helper agent that visualises or shuffles Bob's guess history.

Carol receives plain-text JSON payloads from AgentBob and returns either
(1) a human-readable table of the guesses so far or (2) a JSON list with
entries randomly shuffled, depending on the request.  This functionality
is intentionally simple to keep the focus on A2A message flow.
"""
import json
import uuid
import time
from typing import Dict, Any, List

# Shared helpers
from utils import (
    ToyA2AAgent,
    build_complete_agent_card,
    create_text_task,
    get_first_text_part,
    try_parse_json,
    run_agent_forever,
)
from config import AGENT_CAROL_PORT, AGENT_BOB_PORT


# ------------------ Agent card ------------------

carol_skills = [
    {
        "id": "history_visualiser",
        "name": "Guess History Visualiser",
        "description": "Generates a formatted text summary of guess/response history to aid the player.",
        "tags": ["visualisation", "demo"],
        "inputModes": ["text/plain"],
        "outputModes": ["text/plain"],
        "examples": ['[{"guess": 25, "response": "Go higher"}]'],
    },
    {
        "id": "history_shuffler",
        "name": "Guess History Shuffler",
        "description": "Randomly shuffles the order of guess/response entries in a provided history list and returns JSON.",
        "tags": ["shuffling", "demo"],
        "inputModes": ["text/plain"],
        "outputModes": ["text/plain"],
        "examples": [
            '{"action": "shuffle", "history": [{"guess": 25, "response": "Go higher"}]}'
        ],
    },
]

carol_card = build_complete_agent_card(
    "AgentCarol",
    AGENT_CAROL_PORT,
    description="Visualises the history of guesses and hints from AgentAlice in a readable table format.",
    skills=carol_skills,
)

# ------------------ Helper functions ------------------


def _build_visualisation(history: List[Dict[str, str]]) -> str:
    """Return a readable text representation of the game history."""

    if not history:
        return "No guesses yet."

    lines = ["Guesses so far:"]
    for idx, entry in enumerate(history, 1):
        guess = entry.get("guess", "?")
        response = entry.get("response", "?")
        lines.append(f" {idx:>2}. {guess:>3} -> {response}")
    print("Created a visualisation for Bob")
    return "\n".join(lines)


def _process_payload(raw_text: str) -> str:
    """Given the raw text from Bob, return Carol's response text."""

    import random

    # Attempt to parse the text as JSON – may be a list or an instruction dict
    success, parsed = try_parse_json(raw_text)
    if not success:
        parsed = None

    # 1. Shuffle request
    if isinstance(parsed, dict) and parsed.get("action") == "shuffle":
        history_list = parsed.get("history", [])
        if not isinstance(history_list, list):
            history_list = []
        random.shuffle(history_list)
        print("[AgentCarol] Shuffled history and returned JSON list")
        return json.dumps(history_list)

    # 2. Visualisation request (history list)
    if isinstance(parsed, list):
        history = parsed
    else:
        # Fallback: maybe the raw text *is* the JSON list
        success, history = try_parse_json(raw_text)
        if not success or not isinstance(history, list):
            history = []

    return _build_visualisation(history)  # type: ignore[arg-type]


def carol_handler(params: Dict[str, Any], tasks: Dict[str, Any]) -> Dict[str, Any]:
    """Entry-point for incoming `message/send` calls."""

    raw_text = get_first_text_part(params.get("message", {})) or ""
    context_id = params.get("message", {}).get("contextId")
    response_text = _process_payload(raw_text) if raw_text else "Invalid input."
    return create_text_task(response_text, tasks, context_id=context_id)


# ------------------ Main loop ------------------


def run() -> None:
    """Run AgentCarol until interrupted."""

    # Carol's peer is Bob, but she never initiates messages herself. We still need to supply a peer port.
    agent = ToyA2AAgent(
        "AgentCarol",
        AGENT_CAROL_PORT,
        AGENT_BOB_PORT,
        message_handler=carol_handler,
        agent_card=carol_card,
    )

    run_agent_forever(agent)


def main() -> None:
    run()


if __name__ == "__main__":
    main()
