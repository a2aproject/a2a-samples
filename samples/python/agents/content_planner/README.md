# Content Planner Agent

Given a high-level description of the content that's needed, this sample agent creates a detailed content outline. This agent is written using the Google Agent Development Kit (ADK) and the Python A2A SDK.

## Prerequisites

- Python 3.10 or higher
- [UV](https://docs.astral.sh/uv/)
- Access to an LLM and API Key

## Running the Sample

1. Navigate to the samples directory:

    ```bash
    cd samples/python/agents/content_planner
    ```

2. Create an environment file with your API key:

   ```bash
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   ```

3. Run the agent:

   **NOTE:**
   By default, the agent will start on port 10001. To override this, add the `--port=YOUR_PORT` option at the end of the command below.

    ```bash
    uv run .
    ```

4. In a separate terminal, run the A2A client and use it to send a message to the agent:

    ```bash
    # Connect to the agent (specify the agent URL with correct port)
    cd samples/python/hosts/cli
    uv run . --agent http://localhost:10001

    # If you changed the port when starting the agent, use that port instead
    # uv run . --agent http://localhost:YOUR_PORT
    ```

5. To make use of this agent in a content creation multi-agent system, check out the [content_creation](../../../python/hosts/content_creation/README.md) sample.

## Disclaimer
Important: The sample code provided is for demonstration purposes and illustrates the
mechanics of the Agent-to-Agent (A2A) protocol. When building production applications,
it is critical to treat any agent operating outside of your direct control as a
potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard,
messages, artifacts, and task statuses—should be handled as untrusted input. For
example, a malicious agent could provide an AgentCard containing crafted data in its
fields (e.g., description, name, skills.description). If this data is used without
sanitization to construct prompts for a Large Language Model (LLM), it could expose
your application to prompt injection attacks.  Failure to properly validate and
sanitize this data before use can introduce security vulnerabilities into your
application.

Developers are responsible for implementing appropriate security measures, such as
input validation and secure handling of credentials to protect their systems and users.
