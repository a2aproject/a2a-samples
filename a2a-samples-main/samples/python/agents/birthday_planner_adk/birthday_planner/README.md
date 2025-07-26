# ADK Agent with A2A Client

This example shows how to create an A2A Server that uses an ADK-based Agent that communicates with another agent using A2A.

This agent helps plan birthday parties. It has access to a Calendar Agent that it can delegate calendar-related tasks to. This agent is accessed via A2A.

## Prerequisites

- Python 3.10 or higher
- [UV](https://docs.astral.sh/uv/)
- A Gemini API Key

## Running the example

1. Create the `.env` file with your API Key

   ```bash
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   ```

2. Run the Calendar Agent. See examples/google_adk/calendar_agent.

3. Run the example

   ```sh
   uv run .
   ```

## Disclaimer
Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.  Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.