# 🛠 ITK: Integration Test Kit

![Platform](https://img.shields.io/badge/Platform-Linux-orange.svg)
![Go](https://img.shields.io/badge/Language-Go-blue.svg)
![Python](https://img.shields.io/badge/Language-Python-green.svg)
![Elixir](https://img.shields.io/badge/Language-Elixir-purple.svg)

ITK is a technical toolkit designed to verify compatibility across different A2A SDK implementations and versions. It uses a multi-hop traversal model to ensure that messages can be routed across Go, Python, and Elixir agents using varied transport protocols (JSON-RPC, gRPC, and REST).

---

## 🏗 Architecture

The kit operates by dispatching a single, deeply nested instruction through a chain of agents. Each "hop" in the chain requires the receiving agent to resolve the next target's agent card, map the requested transport, and forward the remaining instructions.

```mermaid
graph LR
    Runner[Test Runner] -->|JSON-RPC| Py1[Python Agent]
    Py1 -->|JSON-RPC| Go1[Go Agent]
    Go1 -->|JSON-RPC| Py2[Python Agent]
    Py2 -->|gRPC| Go2[Go Agent]
    Go2 -->|gRPC| Py3[Python Agent]
    Py3 -->|HTTP/REST| PySelf[Python Self-Call]
```

---

## ⛓ Multi-Hop Traversal Test

The primary verification suite executes a 6-hop traversal to test cross-SDK interop and protocol switching in a single session.

### Traversal Path

| Hop | Source | Target | Transport |
| :--- | :--- | :--- | :--- |
| 1 | Test Runner | Python v0.3 | JSON-RPC |
| 2 | Python v0.3 | Go v0.3 | JSON-RPC |
| 3 | Go v0.3 | Python v0.3 | JSON-RPC |
| 4 | Python v0.3 | Go v0.3 | gRPC |
| 5 | Go v0.3 | Python v0.3 | gRPC |
| 6 | Python v0.3 | Python v0.3 | HTTP-JSON (REST) |

---

## 📂 Project Structure

- `agents/python/v03/`: Consolidated Python agent using the v0.3 SDK.
- `agents/python/v10/`: Python agent using the v1.0 SDK.
- `agents/go/v03/`: Go agent implementation using the v0.3 Go SDK.
- `agents/go/v10/`: Go agent implementation using the v1.0 Go SDK.
- `agents/elixir/v10/`: Elixir agent using the [actioncard/a2a-elixir](https://github.com/actioncard/a2a-elixir) v1.0 SDK.
- `run_tests.py`: Orchestration script that spawns agents and executes the traversal.
- `pyproject.toml`: Root-level `uv` workspace configuration.

---

## 🚀 Getting Started

### Prerequisites
- [uv](https://github.com/astral-sh/uv) for Python dependency management.
- Go 1.21+ for the Go agent build.
- Elixir 1.15+ and Erlang/OTP 26+ for the Elixir agent.

### Running the Tests
Execute the integration suite from the project root:
```bash
uv run run_tests.py
```

The script will automatically clean up ports, spawn agents, wait for readiness, and verify the traversal traces.

---

### Elixir Agent

The Elixir v1.0 agent uses the [actioncard/a2a-elixir](https://github.com/actioncard/a2a-elixir) SDK. It supports JSON-RPC transport and can participate in multi-hop traversals with Python and Go agents.

To run the Elixir agent standalone:
```bash
cd agents/elixir/v10
mix deps.get
ITK_HTTP_PORT=10200 mix run --no-halt
```

Or via the run script (same interface as other agents):
```bash
cd agents/elixir/v10
bash run.sh --httpPort 10200 --grpcPort 11200
```

---

## 🛠 Maintenance

### Re-preparing the `bin/` directory
If you need to re-prepare the local `bin/` directory (Node.js distribution), run the following command from the `itk` directory:

```bash
mkdir -p bin && curl -L https://nodejs.org/dist/v20.11.1/node-v20.11.1-linux-x64.tar.xz | tar -xJ -C bin --strip-components=1
```
