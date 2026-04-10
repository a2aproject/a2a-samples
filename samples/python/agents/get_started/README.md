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
# Weather Reporting Poet Agent

This project implements a Google ADK-powered agent that poetically reports weather updates. It leverages Google Search to gather factual weather data and presents it in the form of haikus or short poems, making weather forecasts engaging and unique.

## ✨ Features

*   **Poetic Weather Reports:** Delivers weather forecasts as haikus or poems, making them engaging and memorable.
*   **Factual Accuracy:** Utilizes Google Search to fetch up-to-date and reliable weather information.
*   **A2A Protocol:** Implements Agent-to-Agent communication standards for seamless integration.
*   **Interactive Client:** A command-line interface for real-time interaction with the agent.
*   **Modular Design:** Separated server, client, and agent components for clarity and maintainability.

## 🚀 Technologies Used

*   Python 3.x
*   Google ADK (Agent Developer Kit)
*   `httpx` (for HTTP requests)
*   `asyncio` (for asynchronous operations)
*   `uvicorn` (for running the ASGI server)
*   Google Generative AI

## 🛠 Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd get_started
    ```
2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    ```
3.  **Activate the virtual environment:**
    *   On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        venv\Scripts\activate
        ```
4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## ▶️ Running the Application

The project provides a `Makefile` with convenient commands to manage its components.

### 1. Start the A2A Server

This command starts the core agent server, which exposes an API for clients to interact with.

```bash
make run_server
```

The server will run on `http://localhost:9999`.

### 2. Run the Client Application

This launches the interactive terminal client. It connects to the A2A server, displays the agent's capabilities, and allows you to send queries.

```bash
make run_client
```

Upon starting, the client will display the agent's card and automatically send an initial query for the weather in Warsaw, Poland.

### 3. Run the Agent Directly (for testing)

This command executes the agent's core logic directly without going through the A2A server. It's useful for testing the agent's functionality in isolation.

```bash
make run_agent
```

## 💬 Usage Examples

After running `make run_client`, you will see the agent's card details and then be prompted for input.

### Example Interaction:

```
########################################
#### Weather Reporting Poet via A2A ####
########################################
Agent Card - Name: Weather Reporting Poet
Agent Card - Capabilities: {'streaming': True, 'extended_agent_card': True}
Agent Card - Description: Weather reporting Poet
Agent Card - Skills:
    Skill - Id: weather_reporting_poet
    Skill - Name: Weather Reporting Poet
    Skill - Description: Poet for latest weather updates
    Skill - Examples: ['How is the weather in Warsaw, Poland', 'How is the weather in Hyderabad, India']
########################################
user> How is the Weather in Poland, Warsaw?
################################
#### Weather Reporting Poet ####
################################
To exit use `exit` or `quit`.
---
model> Warsaw skies today,
Partly sunny, then light rain,
Cool breeze, eight degrees.
---
user>
```

You can then type your own weather queries at the `user>` prompt. To exit, type `exit` or `quit`.

## 📝 Contributions

Contributions are welcome! Please open a pull request with your changes and follow the guidelines in [CONTRIBUTING](https://github.com/a2aproject/a2a-samples/blob/main/CONTRIBUTING.md)

## 📄 License

[Apache License - Version 2.0](https://github.com/a2aproject/a2a-samples/blob/main/LICENSE)
