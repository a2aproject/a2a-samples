# A2A Toy Demo – Number-Guessing Game

This repository contains a little game built on the [A2A](https://github.com/google/a2a) protocol. It is using three small local Python "agents" that cooperate to run a _guess-the-number_ game:

* **AgentAlice** – picks a secret number and grades guesses
* **AgentBob**   – CLI front-end; relays user guesses and shows progress
* **AgentCarol** – formats the history and (optionally) shuffles it on request

The code purposefully avoids external dependencies – it is built only on the Python stdlib. For simplicity, it doesn't use LLMs.

---
## Directory layout

```
A2A_test_implementation/
├── agent_Alice.py    # Runs Alice
├── agent_Bob.py      # Runs Bob
├── agent_Carol.py    # Runs Carol
├── utils/            # Helper package (transport, agent façade, etc.)
├── config.py         # Central port configuration
└── README.md         # ← you are here
```

---
## Requirements

* Python 3.9+ (only stdlib modules are used)

> No third-party packages are needed – a `requirements.txt` is therefore unnecessary.

---
## Running the demo

1. **Clone** the repository and `cd` into it.
2. **Open three terminals** (or tabs) and run each agent:

   ```bash
   # Terminal 1
   python agent_Alice.py

   # Terminal 2
   python agent_Carol.py

   # Terminal 3 – will prompt you to play
   python agent_Bob.py
   ```

3. **Play the game** – Bob will ask you for numbers until Alice replies `correct!`.

During play Bob repeatedly pings Carol to ensure her visualisation is sorted; this exercises multi-turn inter-agent communication.


---
## A2A compliance status

The demo purposefully targets the **minimum viable** subset of A2A v0.2.6 so it remains easy to study. The table below summarises what is covered and what is left for you to implement if you need a production-ready agent.

| Area | Implemented | Notes |
|------|-------------|-------|
| AgentCard (`/.well-known/agent.json`) | ✅ | All required fields filled; optional provider/security omitted |
| `message/send` | ✅ | Full validation of required message fields; returns a completed Task |
| `tasks/get` | ✅ | Simple in-memory task registry |
| Error codes (-32700, -32601, -32602, -32004, -32005) | ✅ | Mapped exactly as in spec |
| Streaming (`message/stream`, `tasks/*subscribe`) | ❌ | Handler returns **-32004** `Unsupported operation` |
| Task cancellation (`tasks/cancel`) | ❌ | Could be added by storing a cancellable flag in `_tasks` |
| Push notifications (`tasks/pushNotificationConfig/*`) | ❌ | Capabilities flag `pushNotifications:false`; no webhook logic yet |
| TLS & authentication | ❌ | Demo binds to plain HTTP on localhost; `securitySchemes` absent |
| State transition history | ❌ | `stateTransitionHistory:false` – `_tasks` only keep final status |
| Additional transports (gRPC) | ❌ | Only JSON-RPC transport is exposed |


---
## License

This demo is released into the public domain.