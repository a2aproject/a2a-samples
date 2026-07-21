# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains code samples and demos for the [Agent2Agent (A2A) Protocol](https://goo.gle/a2a), demonstrating agent-to-agent communication across multiple programming languages and frameworks. The code is for demonstration purposes only and is not production-quality.

**Related repositories:**
- [A2A](https://github.com/a2aproject/A2A) - Specification and documentation
- [a2a-python](https://github.com/a2aproject/a2a-python) - Python SDK
- [a2a-inspector](https://github.com/a2aproject/a2a-inspector) - UI tool for inspecting A2A agents

## Repository Structure

```
a2a-samples/
├── samples/
│   ├── python/        # Primary: 30+ agents using various frameworks
│   │   ├── agents/    # A2A server implementations
│   │   ├── hosts/     # A2A client implementations (CLI, web, orchestrator)
│   │   └── common/    # ⚠️ Deprecated - use a2a-python SDK instead
│   ├── java/          # Maven-based samples with A2A SDK 0.3.2.Final
│   ├── js/            # TypeScript samples using Genkit, Express
│   ├── go/            # JSON-RPC 2.0 compliant implementation
│   └── dotnet/        # .NET 9.0 samples with Semantic Kernel
├── extensions/        # Protocol extensions (AGP, secure-passport, timestamp, traceability)
├── demo/ui/          # Mesop web app demo
└── notebooks/        # Jupyter notebooks for evaluation
```

### Architecture Pattern: Agents and Hosts

**Agents** run A2A servers that expose capabilities via the A2A protocol. They implement `A2AServer` and handle tasks.

**Hosts** run A2A clients that connect to agents. They implement `A2AClient` and make requests to agents.

**Example workflow:**
1. Start one or more agent servers (e.g., `samples/python/agents/langgraph`)
2. Start a host application (e.g., `samples/python/hosts/cli`)
3. Host discovers agent via AgentCard and delegates tasks over A2A protocol

## Common Development Commands

### Python (Primary Language)

**Prerequisites:**
- Python ≥3.12
- [UV](https://docs.astral.sh/uv/) package manager

**UV Workspace:**
The repository uses UV workspaces with 18 member projects defined in root `pyproject.toml`. This allows dependency management across multiple related projects.

**Common commands:**
```bash
# Run any Python agent or host
cd samples/python/agents/langgraph  # or any agent/host directory
uv run .

# Sync dependencies
uv sync

# Run tests
pytest                                           # All tests in current directory
pytest path/to/test_file.py                     # Specific test file
pytest -k test_function_name                    # Specific test

# Format code (git-aware, only changed files)
./format.sh

# Format all files
./format.sh --all

# Format with unsafe fixes
./format.sh --unsafe-fixes
```

**Running the demo:**
```bash
cd demo/ui

# Create .env with authentication (Option A: Google AI Studio)
echo "GOOGLE_API_KEY=your_api_key_here" >> .env

# Or Option B: Vertex AI
echo "GOOGLE_GENAI_USE_VERTEXAI=TRUE" >> .env
echo "GOOGLE_CLOUD_PROJECT=your_project_id" >> .env
echo "GOOGLE_CLOUD_LOCATION=your_location" >> .env

# Run demo (defaults to port 12000)
uv run main.py
```

**Example: Running agent + host:**
```bash
# Terminal 1: Start agent
cd samples/python/agents/langgraph
uv run .

# Terminal 2: Start CLI host
cd samples/python/hosts/cli
uv run .
```

### JavaScript/TypeScript

**Prerequisites:**
- Node.js
- pnpm 10.7.1

**Commands:**
```bash
cd samples/js
pnpm install
pnpm run build
```

### Java

**Prerequisites:**
- Maven 3
- Modern JVM

**Commands:**
```bash
cd samples/java
mvn clean install
mvn test
```

### Go

**Prerequisites:**
- Go 1.24.0

**Commands:**
```bash
cd samples/go
go mod download
go test ./...
go run .
```

### .NET

**Prerequisites:**
- .NET 9.0 SDK

**Commands:**
```bash
cd samples/dotnet
dotnet restore
dotnet build
dotnet run
dotnet test
```

## Code Quality Standards

### Python Style Guide

This project follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html):
- **Line length:** 80 columns
- **Indentation:** 4 spaces
- **Docstrings:** Google style
- **Quotes:** Single quotes for code, double quotes for docstrings
- **Import sorting:** Absolute imports preferred, sorted by isort

### Linting and Formatting

**Primary tool:** Ruff (configured in `.ruff.toml`)

**Enabled rule sets:**
- pycodestyle (E, W)
- Pyflakes (F)
- isort (I)
- pydocstyle (D) - Google convention
- pep8-naming (N)
- pyupgrade (UP)
- flake8-annotations (ANN)
- flake8-bugbear (B)
- flake8-simplify (SIM)
- Pylint (PL)
- flake8-bandit (S) - security checks
- tryceratops (TRY)
- Many more (see `.ruff.toml`)

**Notable ignored rules:**
- `TRY002`: Create your own exception
- `TRY003`: Avoid specifying long messages outside the exception class
- `T201`: Print presence (allowed)
- `E501`: Line length (handled dynamically)

**Format script workflow:**
1. `autoflake` - Remove unused imports
2. `ruff check --fix-only` - Auto-fix lint issues
3. `ruff format` - Format code
4. For notebooks: `nbqa` + `tensorflow_docs.nbfmt`

## Demo Application Architecture

The demo web app (`demo/ui`) demonstrates multi-agent A2A communication:

**Components:**
- **Frontend:** Mesop (Python web framework) on port 12000
- **Host Agent:** Google ADK agent that orchestrates requests
- **Remote Agents:** A2AClient connections wrapped in ADK agents
- **Communication:** All agent-to-agent via A2A protocol

**Features:**
- Dynamic agent discovery and registration via AgentCard
- Multi-agent conversation routing
- Complex content rendering (images, forms, text)
- A2A task history and event tracking

**Container deployment:**
```bash
cd samples/python
podman build -f demo/ui/Containerfile . -t a2a-ui
podman run -p 12000:12000 --network host a2a-ui
```

## Security Considerations

**⚠️ CRITICAL:** Treat any agent outside your direct control as untrusted.

All data from external agents must be validated:
- AgentCard fields (description, name, skills.description, etc.)
- Messages and artifacts
- Task statuses

**Risk:** Malicious agents can craft data to exploit prompt injection attacks if used unsanitized in LLM prompts.

**Your responsibility:** Implement input validation and secure credential handling.

## Extensions

The repository includes protocol extensions in `extensions/`:
- **AGP** (Advanced Generation Protocol): Has own test suite and spec
- **Secure Passport**: Authentication/signing examples
- **Timestamp**: Timestamp extension
- **Traceability**: Tracking and observability

Extensions are part of the UV workspace and can be developed independently.

## Python Sample Frameworks

The `samples/python/agents/` directory contains 30+ agent implementations using:
- CrewAI
- LangGraph
- LlamaIndex
- Marvin
- AG2 (formerly AutoGen)
- Semantic Kernel
- MindsDB
- ADK (Google Agent Development Kit)

Each demonstrates different agent patterns and capabilities while adhering to the A2A protocol.

## Contributing

All contributions require a signed [Contributor License Agreement](https://cla.developers.google.com/). See `CONTRIBUTING.md` for details.

**Code review:** All submissions require review via GitHub pull requests.

**CI/CD:** GitHub Actions run Super Linter on PRs to `main` branch (see `.github/workflows/linter.yaml`).
