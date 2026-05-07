# Agent2Agent (A2A) Samples Context

This repository contains a comprehensive collection of code samples, demos, and tools for the [Agent2Agent (A2A) Protocol](https://goo.gle/a2a). It showcases how agents can interact, orchestrate tasks, and collaborate using a standardized communication layer across different programming languages and transport protocols.

## Project Overview

*   **Goal:** Demonstrate the mechanics and capabilities of the A2A Protocol through practical implementations.
*   **Key Components:**
    *   **Samples:** Implementations in multiple languages including Python, Go, JavaScript/TypeScript, Java, and .NET.
    *   **Demo UI (`demo/ui`):** A web application (using Mesop) for interactive multi-agent conversations.
    *   **ITK (`itk`):** An Integration Test Kit designed to verify compatibility across different A2A SDK implementations and versions.
    *   **Standalone ITK:** Portable versions of the ITK for specific environments.
    *   **Extensions:** Reusable A2A extensions (e.g., timestamping).
*   **Technologies:** Python (uv, FastAPI, Mesop, ADK), Go, JavaScript (Node.js, TypeScript), Java, .NET, Docker/Podman.

## Directory Structure

*   `samples/`: Language-specific A2A agent and host implementations.
*   `itk/`: The Interop Test Kit for cross-version and cross-protocol verification.
*   `demo/`: Interactive demo applications, including a UI.
*   `standalone-itk/`: Standalone/portable Interop Test Kit implementations.
*   `extensions/`: Shared A2A protocol extensions.
*   `notebooks/`: Jupyter notebooks for exploration and demonstration.

## Building and Running

### Python Environment
Most Python components use `uv` for workspace and dependency management.
*   Run the Demo UI: `cd demo/ui && uv run main.py`
*   Run ITK tests: `cd itk && uv run run_tests.py`
*   Run sample agents: Navigate to the specific agent directory in `samples/python/agents/` and use `uv run .`

### Go Environment
*   Standard Go commands apply: `go run`, `go build`, `go test`.
*   Found in `samples/go` and `standalone-itk-go`.

### JavaScript Environment
*   Uses `npm` and `package.json`.
*   Found in `samples/js` and `demo/ui` (for frontend).

## Development Conventions

*   **Python Formatting:** Python and Jupyter Notebook files are formatted using `ruff` and `autoflake`. Use the provided `./format.sh` script for consistent formatting.
*   **Configuration:** Tooling configs are at the root: `.ruff.toml`, `.editorconfig`, `.prettierrc`.
*   **Testing:** ITK is the primary tool for verifying A2A interop. Language-specific samples should follow their respective idiomatic testing patterns.
*   **Security:** Always treat data from external agents as untrusted input. Validate and sanitize `AgentCard` data and message content to prevent prompt injection and other vulnerabilities.

## Related Resources

*   [A2A Protocol Specification](https://goo.gle/a2a)
*   [a2a-python SDK](https://github.com/a2aproject/a2a-python)
*   [A2A Inspector](https://github.com/a2aproject/a2a-inspector)
