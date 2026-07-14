# Sample Code

This code is used to demonstrate A2A capabilities as the spec progresses.

Samples are divided into 3 sub directories:

* [**Common**](/samples/python/common)
    * NOTE: Do not use this code for further development. Use the A2A Python SDK here: https://github.com/google/a2a-python/

* [**Agents**](/samples/python/agents/README.md)
Sample agents written in multiple frameworks that perform example tasks with tools. These all use the common A2AServer.

* [**Hosts**](/samples/python/hosts/README.md)
Host applications that use the A2AClient. Includes a CLI which shows simple task completion with a single agent, a mesop web application that can speak to multiple agents, and an orchestrator agent that delegates tasks to one of multiple remote A2A agents.

## Prerequisites

- **Python**: Version 3.10 or higher (some samples may require Python 3.13)
- **pip** (for samples configured with `requirements.txt`)
- **[uv](https://docs.astral.sh/uv/)** (for samples configured with `pyproject.toml`)

## Running the Samples

Run one (or more) [agent](/samples/python/agents/README.md) A2A server and one of the [host applications](/samples/python/hosts/README.md).

Depending on how the specific sample is configured, you can run it either using **standard python & pip** (if a `requirements.txt` file is present) or **uv** (if a `pyproject.toml` file is present).

### Option A: Using standard pip & virtualenv (for samples with `requirements.txt`)

For example, to run the `helloworld` agent with a virtual environment:

1. Navigate to the agent directory:
    ```bash
    cd samples/python/agents/helloworld
    ```
2. Set up a virtual environment and install dependencies:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
3. Run the agent server:
    ```bash
    python __main__.py
    ```

> [!TIP]
> **Alternative: Using `uv` with `requirements.txt`**
> If you prefer using `uv` but want to avoid parent workspace conflicts, you can use `uv` in non-project mode:
> - **With a virtual environment**:
>   ```bash
>   uv venv
>   source .venv/bin/activate
>   uv pip install -r requirements.txt
>   python __main__.py
>   ```


### Option B: Using uv (for samples with `pyproject.toml`)

For example, to run the `langgraph` agent:

1. Navigate to the agent directory:
    ```bash
    cd samples/python/agents/langgraph
    ```
2. Run the agent server:
    ```bash
    uv run .
    ```

---
**NOTE:**
This is sample code and not production-quality libraries.
---


## Disclaimer
Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.  Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.
