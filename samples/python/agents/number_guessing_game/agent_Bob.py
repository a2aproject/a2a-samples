"""agent_Bob.py
AgentBob – command-line front-end for the toy A2A number-guessing game.

Bob mediates between a human player and two peer agents:

* **AgentAlice** – holds the secret number and grades guesses.
* **AgentCarol** – produces textual visualisations (and optional shuffles)
  of Bob's accumulated guess history.
"""

from __future__ import annotations

import json
import time

from typing import Any

from a2a.types import Task, TaskState
from config import AGENT_ALICE_PORT, AGENT_CAROL_PORT
from utils.game_logic import is_sorted_history
from utils.protocol_wrappers import (
    cancel_task,
    extract_text,
    send_followup,
    send_text,
)


# ---------------------------------------------------------------------------
# Local in-memory game state
# ---------------------------------------------------------------------------

game_history: list[dict[str, str]] = []

MAX_NEGOTIATION_ATTEMPTS = 400  # Upper bound to avoid endless loops


def _start_shuffle_request() -> Task | None:
    """Send the initial shuffle request to AgentCarol and ensure we get back a Task."""
    payload = json.dumps({'action': 'shuffle', 'history': game_history})
    resp_obj = send_text(AGENT_CAROL_PORT, payload)  # type: ignore[arg-type]
    return resp_obj if isinstance(resp_obj, Task) else None


def _extract_history_from_task(resp_task: Task) -> list[Any]:
    """Return the JSON-decoded history list from *resp_task*.

    Args:
        resp_task: Task object produced by Agent Carol that is expected to
            contain a single JSON list in its most recent artifact.

    Returns:
        list: The parsed history list or an empty list when parsing fails or the
        artifact is missing/invalid.
    """
    parts_text = extract_text(resp_task)
    try:
        return json.loads(parts_text)
    except json.JSONDecodeError:
        return []


def _negotiate_sorted_history(
    max_attempts: int = MAX_NEGOTIATION_ATTEMPTS,
) -> int:
    """Ask Carol to shuffle until the history list is sorted.

    The function starts a new *shuffle* task, then enters a request/response
    loop sending either “Try again” or “Well done!” follow-ups depending on
    whether the returned list is sorted.

    Args:
        max_attempts: Upper bound on the number of reshuffle attempts before the
            task is cancelled to avoid an infinite loop.

    Returns:
        int: The number of messages sent to Carol during the negotiation.
    """
    attempts = 0
    resp_task = _start_shuffle_request()
    if resp_task is None:
        return attempts

    print(
        f'[Bob] Received Task {resp_task.id} with state={resp_task.status.state}'
    )

    while (
        resp_task.status.state == TaskState.input_required
        and attempts < max_attempts
    ):
        # Evaluate the list *before* deciding what follow-up to send
        maybe_hist = _extract_history_from_task(resp_task)
        if isinstance(maybe_hist, list):
            print(f'[Bob] Candidate history: {maybe_hist}')
            print(f'[Bob] is_sorted? {is_sorted_history(maybe_hist)}')

        if isinstance(maybe_hist, list) and is_sorted_history(maybe_hist):
            attempts += 1
            game_history.clear()
            game_history.extend(maybe_hist)
            print(f'[Bob] History is sorted after {attempts} attempt(s)')
            print(
                '(We do sorting by random to illustrate multi-turn communication)'
            )
            resp_task = send_followup(AGENT_CAROL_PORT, resp_task, 'Well done!')  # type: ignore[assignment]
            break

        # Not sorted → ask Carol to shuffle again
        attempts += 1
        print(f"[Bob] Attempt {attempts}: sending 'Try again'")
        resp_obj = send_followup(AGENT_CAROL_PORT, resp_task, 'Try again')
        if not isinstance(resp_obj, Task):
            print(
                '[Bob] Did not receive Task in response; aborting negotiation'
            )
            break
        resp_task = resp_obj
        print(f'[Bob] Carol responded with state={resp_task.status.state}')

    if (
        resp_task.status.state == TaskState.input_required
        and attempts >= max_attempts
    ):
        print(
            f'[Bob] Reached maximum attempts ({max_attempts}). Cancelling task.'
        )
        cancel_task(AGENT_CAROL_PORT, resp_task.id)

    return attempts


def _handle_guess(guess: str) -> str:
    """Forward *guess* to Agent Alice and return her textual feedback."""
    resp_obj = send_text(AGENT_ALICE_PORT, guess)
    feedback = extract_text(resp_obj)
    print(f'Alice says: {feedback}')
    return feedback


def _visualise_history() -> None:
    """Request and print a formatted visualisation of *game_history*."""
    vis_obj = send_text(AGENT_CAROL_PORT, json.dumps(game_history))
    vis_text = extract_text(vis_obj)
    print("\n=== Carol's visualisation (sorted) ===")
    print(vis_text)
    print('============================\n')


def play_game() -> None:
    """Run the interactive CLI loop for the number-guessing game."""
    print('Guess the number AgentAlice chose (1-100)!')

    while True:
        user_input = input('Your guess: ').strip()
        if not user_input:
            continue

        feedback = _handle_guess(user_input)
        game_history.append({'guess': user_input, 'response': feedback})

        total_attempts = _negotiate_sorted_history()
        if total_attempts:
            print(
                f'Asked Carol to re-do the visualisation {total_attempts} times'
            )

        _visualise_history()

        if feedback.startswith('correct'):
            break

    print('You won! Exiting…')
    time.sleep(0.5)


def main() -> None:  # pragma: no cover
    print("Hint: don't forget to also start Alice and Carol!")
    play_game()


if __name__ == '__main__':
    main()
