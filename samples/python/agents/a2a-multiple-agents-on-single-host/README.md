# a2a-multiple-agents-on-single-host

This repository demonstrates how to run **multiple A2A agents** on the **same host** using the A2A protocol.
Each agent is served at a **unique URL path**, making it possible to host different agents without requiring multiple servers or ports.

---

## 📌 Example Setup

Three agents running on the same host:

| Agent Name            | Agent card URL                                                                                                    |
|-----------------------|-------------------------------------------------------------------------------------------------------------------|
| Conversational Agent  | [http://localhost:8000/a2a/conversation/agent-card.json](http://localhost:8000/a2a/conversation/agent-card.json) |
| Trending topics Agent | [http://localhost:8000/a2a/trending/agent-card.json](http://localhost:8000/a2a/trending/agent-card.json) |
| Analyzer Agent        | [http://localhost:8000/a2a/analyzer/agent-card.json](http://localhost:8000/a2a/analyzer/agent-card.json) |


---

## 🚀 Running Agents Locally

1. Navigate to the sample code directory 
    ```bash
    cd samples/python/agents/a2a-multiple-agents-on-single-host
    ```

2.  Install dependencies (using uv)
    ```bash
    uv venv
    source .venv/bin/activate
    uv sync
    ```

3.  Set environment variables
    *   Copy `.env-sample` to `.env`
        ```bash
        cp .env-sample .env
        ```
    *   Update values as needed

4.  Start the agents
    ```bash
    uv run main.py
    ```

---

### Testing using CLI :

```shell
cd samples/python/hosts/cli
uv run . --agent http://localhost:8000/a2a/conversation/
```
   
---
## 📂 Project Structure

```text
├── README.md
├── a2a_client_app.py
├── main.py
├── pyproject.toml
├── src
│ ├── __init__.py
│ ├── a2a
│ │ ├── __init__.py
│ │ ├── a2a_client.py
│ │ └── a2a_fastapi_app.py
│ └── agent
│     ├── __init__.py
│     ├── analyzer_agent.py
│     ├── conversation_agent.py
│     └── trending_topics_agent.py
└── uv.lock

```

---

## ✅ Requirements

Key dependencies defined in `pyproject.toml`:

*   `a2a-sdk`
*   `google-adk`

---

## Notes

- This setup demonstrates hosting multiple agents via unique URL paths behind a single application server.
- If you run behind a reverse proxy, ensure the `/a2a/...` paths are forwarded to the app.
- For local development, keep your working directory at the project root so relative imports and paths resolve correctly.