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

The server is structured into three core Python modules, each with specific responsibilities:

### 1. `agent.py`
Defines the underlying LLM agent using the Google ADK.
* **Core Logic:** Uses `gemini-2.5-flash-lite` to generate poetic weather forecasts.
* **Tools:** Integrates `google_search` to ensure factual accuracy by retrieving real-time weather data.
* **Execution:** Provides both synchronous (`run`) and asynchronous streaming (`stream`) execution methods.

### 2. `agent_executor.py`
Acts as the bridge between the core agent logic and the A2A server protocol.
* **A2A Integration:** Implements the `AgentExecutor` interface.
* **Task Management:** Handles A2A `Task` lifecycles, translating agent streaming events into A2A `TaskStatusUpdateEvent` objects.

### 3. `app.py`
The entry point for running the A2A agent server.
* **Framework:** Built on top of Starlette and Uvicorn.
* **Configuration:** Defines the public `AgentCard` and `AgentSkill`, advertising the agent's capabilities (e.g., streaming) to A2A clients.
* **Routing:** Sets up JSON-RPC endpoints for A2A communication and a basic `/health` check.

## 🚀 Running the Server

You can start the server from the root directory using the Makefile:

```bash
make run_server
```

Or run it directly from this directory:

```bash
python app.py
```

The server will be available at `http://localhost:9999`.
