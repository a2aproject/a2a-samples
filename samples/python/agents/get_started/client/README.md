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

# A2A Weather Poet Client

This directory contains a simple, interactive Python client that communicates with the Weather Reporting Poet agent using the A2A Python SDK.

## 📁 Component Overview

### `client_app.py`
A terminal-based client application demonstrating how to interact with an A2A-enabled server.
*   **Agent Discovery:** Uses `A2ACardResolver` to dynamically fetch the server's `AgentCard` and verify its capabilities.
*   **Interactive Session:** Establishes a communication channel using `create_client` and sends queries to the server.
*   **Response Handling:** Asynchronously receives and displays the poetic weather updates streamed from the agent.

## 🚀 Running the Client

Ensure the A2A Server is running first. Then, you can launch the client from the root directory using the Makefile:

```bash
make run_client
```

Or run it directly from this directory:

```bash
python client_app.py
```

Upon execution, the client will display the agent's advertised skills and start an interactive prompt pre-loaded with a query for the weather in Warsaw, Poland.
