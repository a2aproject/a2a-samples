"""utils.game_logic
Game mechanics shared by the toy number-guessing demo.

This module is transport-agnostic. It currently contains:
* Number-guess evaluation for Agent Alice (`process_guess`).
* History visualisation and shuffle helpers for Agent Carol
  (`build_visualisation`, `process_history_payload`).
"""

from __future__ import annotations

import json
import random

from utils.helpers import parse_int_in_range, try_parse_json


__all__ = [
    'build_visualisation',
    'is_sorted_history',
    'process_guess',
    'process_history_payload',
]

# ---------------------------------------------------------------------------
# Number-guessing state (Alice)
# ---------------------------------------------------------------------------

_target_number: int = random.randint(1, 100)
_attempts: int = 0
_secret_logged: bool = False


# ---------------------------------------------------------------------------
# Number-guessing helpers
# ---------------------------------------------------------------------------


def process_guess(raw_text: str) -> str:
    """Evaluate a single guess and return Agent Alice's feedback.

    Args:
        raw_text: Raw user input that should represent an integer between 1
            and 100 (inclusive).

    Returns:
        str: One of the following response strings:
            * ``"Go higher"`` – the guess was lower than the secret.
            * ``"Go lower"`` – the guess was higher than the secret.
            * ``"correct! attempts: <n>"`` – the guess is correct; *n* is the
              number of attempts so far.
            * An error prompt when the input is invalid.
    """
    global _attempts, _target_number, _secret_logged

    if not _secret_logged:
        print('[GameLogic] Secret number selected. Waiting for guesses…')
        _secret_logged = True

    guess = parse_int_in_range(raw_text, 1, 100)
    if guess is None:
        print(f"[GameLogic] Received invalid input '{raw_text}'.")
        return 'Please send a number between 1 and 100.'

    _attempts += 1

    if guess < _target_number:
        hint = 'Go higher'
    elif guess > _target_number:
        hint = 'Go lower'
    else:
        hint = f'correct! attempts: {_attempts}'

    print(f'[GameLogic] Guess {guess} -> {hint}')
    return hint


# ---------------------------------------------------------------------------
# History helpers (Carol and Bob)
# ---------------------------------------------------------------------------


def build_visualisation(history: list[dict[str, str]]) -> str:
    """Create a human-readable rendering of a guess/response history list.

    Args:
        history: Sequence of dictionaries, each containing at least the keys
            ``"guess"`` and ``"response"``.

    Returns:
        str: Multi-line string ready to be printed to the console.
    """
    if not history:
        return 'No guesses yet.'

    lines = ['Guesses so far:']
    for idx, entry in enumerate(history, 1):
        guess = entry.get('guess', '?')
        response = entry.get('response', '?')
        lines.append(f' {idx:>2}. {guess:>3} -> {response}')
    print('[GameLogic] Created a visualisation for Bob')
    return '\n'.join(lines)


def is_sorted_history(history: list[dict[str, str]]) -> bool:
    """Return ``True`` when *history* is sorted in ascending order by the guess.

    The helper gracefully handles histories that contain plain numbers or
    numeric strings instead of full dictionaries.

    Args:
        history: List of dictionaries **or** plain numbers representing the
            guessed value.

    Returns:
        bool: ``True`` when values are in non-decreasing order; ``False``
        otherwise or on parse errors.
    """
    # The history list can contain either dict entries (with a 'guess' key)
    # or bare numeric values when other agents reply with a simplified list.
    try:
        if history and isinstance(history[0], dict):
            guesses = [int(entry['guess']) for entry in history]
        else:
            # Assume iterable of plain numbers / numeric strings
            guesses = [int(entry) for entry in history]
    except (ValueError, TypeError, KeyError):
        return False
    return guesses == sorted(guesses)


def process_history_payload(raw_text: str) -> str:
    """Return Agent Carol's response for the supplied payload.

    The interpretation depends on the JSON structure:

    1. ``{"action": "shuffle", "history": [...]}`` – The history list is
       shuffled in place and returned as a JSON string.
    2. ``[ ... ]`` – The list is treated as a full history and formatted via
       :func:`build_visualisation`.

    Any input that cannot be parsed as JSON yields an empty visualisation to
    signal invalid input.

    Args:
        raw_text: Raw payload received from Bob.

    Returns:
        str: Either a JSON-encoded list or a plain-text visualisation.
    """
    success, parsed = try_parse_json(raw_text)
    if not success:
        # Not JSON – return an empty visualisation to signal invalid input.
        return build_visualisation([])

    # Shuffle request
    if isinstance(parsed, dict) and parsed.get('action') == 'shuffle':
        history_list = parsed.get('history', [])
        if not isinstance(history_list, list):
            history_list = []
        random.shuffle(history_list)
        print('[GameLogic] Shuffled history and returned JSON list')
        return json.dumps(history_list)

    # Visualisation request
    if isinstance(parsed, list):
        return build_visualisation(parsed)

    # Fallback for unsupported JSON payloads
    return build_visualisation([])
