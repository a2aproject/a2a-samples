# AutoGen Currency Agent

A specialized agent for currency conversion built with AutoGen framework and the A2A Python SDK.

## Prerequisites

- Python 3.10 or higher
- `OPENAI_API_KEY` environment variable set
- A2A Python SDK (`a2a-sdk`)

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
python -m agents.autogen
```

## Files

- `agents/autogen/__init__.py`: Package initialization
- `agents/autogen/__main__.py`: Entry point and server setup
- `agents/autogen/agent.py`: Core AutoGen agent logic
- `agents/autogen/agent_executor.py`: Adapter for A2A SDK
- `requirements.txt`: Dependencies
- `README.md`: Usage guide


This project is part of the AutoGen agent samples and follows the same licensing terms.

## Disclaimer

Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.  Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.
