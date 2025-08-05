# A2A Number-Guessing Demo (Python)

This repository showcases three lightweight A2A agents that cooperate to play a classic _guess-the-number_ game.  

To make it an accessible practical introduction into A2A and the Python SDK, we keep this app intentionally minimalistic:

- no LLMs, API keys etc
- no need for remote servers (all 3 agents run locally)
- easy to install and try
- minimal external dependencies
- the minimal set of features to demonstrate some core concepts of A2A.

| Agent | Role |
|-------|------|
| **AgentAlice** | Picks a secret integer (1-100) and grades incoming guesses. |
| **AgentBob**   | CLI front-end – relays player guesses, shows Alice’s hints, negotiates with Carol. |
| **AgentCarol** | Generates a text visualisation of the guess history and, on request, shuffles it until Bob is happy. |

## Requirements

- Python **3.10+**
- `pip`

   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

The runtime dependencies are minimal: the official `a2a-sdk` package and `uvicorn` for the HTTP server.

## Running the demo

1. Clone the repository and `cd` into it.
2. Open **three terminals** (or panes). In each one, activate the virtual environment first:

   ```bash
   source .venv/bin/activate   # (Windows: .venv\\Scripts\\activate)
   ```

   Then start the agents:

   ```bash
   # Terminal 1 – Alice (evaluator)
   python agent_Alice.py

   # Terminal 2 – Carol (visualiser / shuffler)
   python agent_Carol.py

   # Terminal 3 – Bob (CLI front-end)
   python agent_Bob.py
   ```

3. Play!  Bob will prompt you for numbers until Alice replies with `correct! attempts: N`.

During play Bob will repeatedly ask Carol to reshuffle the history until it is sorted – this exercises multi-turn, task-referencing messages between agents.

## Directory layout (abridged)

```text
number_guessing_game/
├── agent_Alice.py                  # Evaluator agent
├── agent_Bob.py                    # CLI front-end agent
├── agent_Carol.py                  # Visualiser / shuffler agent
├── utils/
│   ├── game_logic.py               # Pure game mechanics (transport-agnostic)
│   ├── helpers.py                  # Tiny generic helpers (JSON parsing, etc.)
│   ├── protocol_wrappers.py        # Convenience wrappers around A2A SDK
│   ├── server.py                   # Helper to spin up Starlette + SDK handler
│   └── __init__.py                 # Re-exports
├── config.py                       # Centralised port configuration
├── requirements.txt                # Runtime deps
└── README.md                       # ← you are here
```

## A2A feature coverage (SDK 0.3.x)

Most heavy lifting (validation, error mapping, Task aggregation, etc.) is handled by the SDK.  The demo therefore focuses on **agent logic** – not protocol plumbing.

| Area | Status |
|------|--------|
| `message/send` | Implemented via SDK helper. |
| Task aggregation | Handled by `ClientTaskManager`. |
| Streaming & subscriptions | **Not implemented** – SDK returns `Unsupported operation`. |
| Push notification config | Not implemented (capability flag is `false`). |
| Transports | JSON-RPC via Starlette/Uvicorn (gRPC left as exercise). |
| TLS & auth | Plain HTTP on `localhost` only. |

## License

Released into the public domain.
