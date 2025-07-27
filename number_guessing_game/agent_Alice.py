"""agent_Alice.py
AgentAlice – the evaluator in the toy A2A number-guessing demo.

This agent picks a secret integer between 1 and 100 when the process
starts and evaluates incoming guesses sent via the A2A `message/send`
operation.  For each guess it responds with one of the following hints:

* ``"Go higher"`` – the guess was lower than the secret.
* ``"Go lower"``  – the guess was higher than the secret.
* ``"correct! attempts: <n>"`` – the guess was correct; ``n`` is the
  number of attempts taken so far.

The module exposes a single public callable, :pyfunc:`alice_handler`,
which is wired into :class:`utils.ToyA2AAgent` and runs inside an HTTP
server started in the ``__main__`` block.

All functionality is implemented using only the Python standard
library, in accordance with the project constraints.
"""
import random
import uuid
import time
from typing import Dict, Any

# Shared helpers
from utils import (
    ToyA2AAgent,
    build_complete_agent_card,
    create_text_task,
    get_first_text_part,
    parse_int_in_range,
    run_agent_forever,
)
from config import AGENT_ALICE_PORT, AGENT_BOB_PORT

# ------------------ Agent card ------------------

alice_skills = [
    {
        "id": "number_guess_evaluator",
        "name": "Number Guess Evaluator",
        "description": "Evaluates numeric guesses (1-100) against a secret number and replies with guidance (higher/lower/correct).",
        "tags": ["game", "demo"],
        "inputModes": ["text/plain"],
        "outputModes": ["text/plain"],
        "examples": ["50"],
    }
]

alice_card = build_complete_agent_card(
    "AgentAlice",
    AGENT_ALICE_PORT,
    description="Hosts the number-guessing game by picking a secret number and grading guesses.",
    skills=alice_skills,
)

# ------------------ Gameplay helpers ------------------

# Random target number between 1 and 100
_target_number = random.randint(1, 100)
_attempts: int = 0
print("[AgentAlice] Secret number selected. Waiting for guesses…")


def alice_handler(params: Dict[str, Any], tasks: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single user guess and create an A2A **Task** response.

    Args:
        params: The ``params`` object of the incoming JSON-RPC call.  Only
            the ``message`` sub-object is inspected.
        tasks: Shared in-memory task registry managed by
            :class:`utils.ToyA2AAgent`.  The newly created response task is
            stored here so that the caller can subsequently retrieve it
            via ``tasks/get`` if desired.

    Returns:
        A completed Task dictionary containing a single text part with
        Alice's feedback message (one of *Go higher*, *Go lower*, or
        *correct!*).

    Side Effects:
        * Increments the module-level ``_attempts`` counter.
        * Writes diagnostic information to ``stdout`` using ``print``.
    """
    global _attempts, _target_number
    message = params.get("message", {})
    response_text = "Invalid input."

    context_id = message.get("contextId")
    guess_str = get_first_text_part(message)

    if guess_str is not None:
        guess_val = parse_int_in_range(guess_str, 1, 100)
        if guess_val is None:
            response_text = "Please send a number between 1 and 100."
            print(f"[AgentAlice] Received invalid input '{guess_str}'.")
        else:
            _attempts += 1
            if guess_val < _target_number:
                response_text = "Go higher"
            elif guess_val > _target_number:
                response_text = "Go lower"
            else:
                response_text = f"correct! attempts: {_attempts}"

            print(f"[AgentAlice] Guess {guess_val} -> {response_text}")

    return create_text_task(response_text, tasks, context_id=context_id)


if __name__ == "__main__":
    agent = ToyA2AAgent(
        "AgentAlice",
        AGENT_ALICE_PORT,
        AGENT_BOB_PORT,
        message_handler=alice_handler,
        agent_card=alice_card,
    )

    run_agent_forever(agent)
