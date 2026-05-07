# ITK Logging Readability and Standardization Instructions

## Goal
Improve log readability across the Integration Test Kit (ITK) by standardizing log level configuration and isolating file logging to the test suite orchestrator.

## General Requirements

### 1. Environment Variable `ITK_LOG_LEVEL`
- All testing agents and servers must respect the `ITK_LOG_LEVEL` environment variable.
- Supported levels: `DEBUG`, `INFO`, `WARN`, `ERROR` (case-insensitive).
- Default value: `INFO`.

### 2. Agent Logging Behavior
- Agents must **only** configure their log level based on `ITK_LOG_LEVEL` and log to standard output/error.
- Agents **must not** create or write to log files directly.

### 3. Test Suite Orchestrator Responsibility
- The responsibility of dumping agent logs to files lies with the agent spawning functions in the test suite.
- If `ITK_LOG_LEVEL` is set to `DEBUG`, the test suite must redirect the output of spawned agents to separate files within the `itk/logs` directory.
- Example log file names: `agent_python_v03.log`, `agent_go_v10.log`.

### 4. Logs Directory
- A `logs` directory must exist at the root of the `itk` directory.
- It should contain a `.gitkeep` file to ensure it is tracked by Git.
- This directory should be mountable to Docker containers to inspect logs.

---

## Language-Specific Requirements

### Python Agents
- Agents must read `ITK_LOG_LEVEL` and configure their Python logger.
- The Uvicorn server (used by Python agents) must also specify the logging level matching `ITK_LOG_LEVEL`.

### Go Agents
- Agents must read `ITK_LOG_LEVEL` and configure their logging accordingly.
- The `v03` agent **must not** use the logging mechanism from the new Go SDK (`v2`). It must use a logging mechanism appropriate to the v0.3 SDK (e.g., standard `log` or whatever was idiomatic for that version).
- The `v10` agent should use logging appropriate for the v1.0 SDK.
- Standard library `log`/`slog` restriction applies only where it contradicts SDK usage for that specific version. Since v0.3 lacks a specialized logger, standard `log` is acceptable there.

