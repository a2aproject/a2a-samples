<!--
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

-->

# A2A Weather Poet Server

This directory contains the server-side implementation of the Weather Reporting Poet agent, powered by the Google ADK and the A2A Python SDK.

## 📁 Component Overview

The server is structured into modular Python modules, each with specific responsibilities:

### 1. `a2a_server.py`
The entry point for running the A2A agent server.
* **Framework:** Built on top of Starlette and Uvicorn.
* **Configuration:** Defines the public `AgentCard` and `AgentSkill`, advertising the agent's capabilities to A2A clients.
* **Routing:** Sets up JSON-RPC endpoints for A2A communication and a basic `/health` check.

### 2. `a2a_executor.py`
Acts as the bridge between the core agent logic and the A2A server protocol.
* **A2A Integration:** Implements the `AgentExecutor` interface.
* **Task Management:** Handles A2A `Task` lifecycles, translating agent streaming events into A2A `TaskStatusUpdateEvent` objects.

### 3. `agent.py`
Interactive multi-framework CLI gateway for testing the underlying agent personalities directly.

### 4. `agent_adk.py`, `agent_crewai.py`, `agent_langraph.py`
Framework-specific implementations of the Weather Poet agent.

## 🚀 Running the Server

You can start the server from the root directory using the Makefile:

```bash
make run_server
```

Or run it directly from this directory:

```bash
python a2a_server.py
```

The server will be available at `http://localhost:9999`.
