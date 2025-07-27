"""agent_Bob.py
AgentBob – command-line front-end for the toy A2A number-guessing game.

Bob mediates between a human player and two peer agents:

* **AgentAlice** – holds the secret number and grades guesses.
* **AgentCarol** – produces textual visualisations (and optional shuffles)
  of Bob's accumulated guess history.

Responsibilities:
1. Prompt the user for numeric guesses via ``stdin``.
2. Forward each guess to Alice using the A2A ``message/send`` operation.
3. Maintain an in-memory list of guess/response pairs (``game_history``).
4. Ask Carol for a visualisation of the history, retrying until the list
   is sorted by ascending guess value to illustrate multi-turn flows.
"""
import time
from typing import Dict, Any
import json

from utils import (
    ToyA2AAgent,
    build_complete_agent_card,
    safe_extract_plain_text as extract_reply,
    get_first_text_part,
)
from config import AGENT_ALICE_PORT, AGENT_BOB_PORT, AGENT_CAROL_PORT


# ------------------ Agent card ------------------

bob_skills = [
    {
        "id": "number_guess_player",
        "name": "Number Guess Player",
        "description": "Collects user guesses and communicates with AgentAlice and AgentCarol to play the number guessing game and visualise progress.",
        "tags": ["game", "demo"],
        "inputModes": ["text/plain"],
        "outputModes": ["text/plain"],
        "examples": ["42"],
    }
]

bob_card = build_complete_agent_card(
    "AgentBob",
    AGENT_BOB_PORT,
    description="User interface agent for the number guessing demo. Relays guesses to Alice and displays Carol's summaries.",
    skills=bob_skills,
)


# ------------------ Gameplay helpers ------------------

game_history: list[Dict[str, str]] = []


# ------------------ Helper utilities ------------------


def _is_sorted(hist: list[Dict[str, str]]) -> bool:
    """Return True if history entries are sorted by numeric guess ascending."""

    try:
        guesses = [int(entry["guess"]) for entry in hist]
    except Exception:
        return False
    return guesses == sorted(guesses)


def _sort_history_via_carol(agent: ToyA2AAgent) -> int:
    """Ensure `game_history` is sorted by repeatedly asking Carol to shuffle it.

    This is to illustrate a repeated interaction between agents.

    Returns the number of shuffle attempts performed.
    """

    attempts = 0
    MAX_ATTEMPTS = 1000
    while attempts < MAX_ATTEMPTS and not _is_sorted(game_history):
        attempts += 1
        shuffle_payload = json.dumps({"action": "shuffle", "history": game_history})
        shuffle_resp = agent.send_message_to(AGENT_CAROL_PORT, shuffle_payload)
        shuffled_json = extract_reply(shuffle_resp)
        try:
            new_history = json.loads(shuffled_json)
            if isinstance(new_history, list):
                game_history.clear()
                game_history.extend(new_history)
            else:
                print("Carol returned unexpected data; aborting sorting loop.")
                break
        except json.JSONDecodeError:
            print("Could not parse Carol's shuffle response; aborting sorting loop.")
            break
    return attempts


def _handle_guess(agent: ToyA2AAgent, guess: str) -> str:
    """Send the user's guess to Alice and return Alice's feedback text."""

    resp = agent.send_message(guess)
    feedback = extract_reply(resp)
    print(f"Alice says: {feedback}")
    return feedback


def _visualise_history(agent: ToyA2AAgent) -> None:
    """Ask Carol for a visualisation of the (sorted) game history and print it."""

    vis_resp = agent.send_message_to(AGENT_CAROL_PORT, json.dumps(game_history))
    vis_text = extract_reply(vis_resp)
    print("\n=== Carol's visualisation (sorted) ===")
    print(vis_text)
    print("============================\n")


# ------------------ Main gameplay loop ------------------


def play_game() -> None:
    """Run the interactive game loop until the user guesses correctly."""
    agent = ToyA2AAgent(
        "AgentBob", AGENT_BOB_PORT, AGENT_ALICE_PORT, agent_card=bob_card
    )
    agent.start()

    print("Guess the number AgentAlice chose (1-100)!")

    while True:
        user_input = input("Your guess: ").strip()
        if not user_input:
            continue

        feedback = _handle_guess(agent, user_input)

        # Keep track and ask Carol for a summary visualisation via A2A
        game_history.append({"guess": user_input, "response": feedback})

        # Ensure Carol provides a sorted visualisation
        total_attempts = _sort_history_via_carol(agent)
        if total_attempts:
            print(f"Asked Carol to re-do the visualisation {total_attempts} times")

        _visualise_history(agent)

        if feedback.startswith("correct"):
            break

    print("You won! Exiting…")
    time.sleep(0.5)


def main() -> None:
    """Entry-point wrapper required by some tooling and importers."""
    play_game()


if __name__ == "__main__":
    main()
