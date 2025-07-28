# Weather Agent

This sample agent connects to a weather MCP server to handle weather-related requests. This agent is written using Quarkus LangChain4j and makes use of the [A2A Java](https://github.com/a2aproject/a2a-java) SDK.

## Prerequisites

- Java 17 or higher
- Access to an LLM and API Key

## Running the Sample

1. Navigate to the `weather_mcp` sample directory:

    ```bash
    cd samples/java/agents/weather_mcp
    ```

2. Create a .env file in the `weather_mcp` directory as follows:

   ```bash
   cp .env.example .env
   ```

   Then update the `.env` file to specify your Google AI Studio API Key (note that no quotes are needed below):

   ```bash
   QUARKUS_LANGCHAIN4J_AI_GEMINI_API_KEY=your_api_key_here
   ```

3. Run the Weather Agent

   **NOTE:**
   By default, the agent will start on port 10001. To override this, add the `-Dquarkus.http.port=YOUR_PORT` option at the end of the command below.

   ```bash
   mvn quarkus:dev
   ```

4. In a separate terminal, run the A2A client and use it to send a message to the agent:

    ```bash
    # Connect to the agent (specify the agent URL with correct port)
    cd samples/python/hosts/cli
    uv run . --agent http://localhost:10001

    # If you changed the port when starting the agent, use that port instead
    # uv run . --agent http://localhost:YOUR_PORT
    ```

5. To make use of this agent in a multi-language, multi-agent system, check out the [weather_and_airbnb_planner](../../../python/hosts/weather_and_airbnb_planner/README.md) sample.

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
