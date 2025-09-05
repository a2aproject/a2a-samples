# Dice Agent (Multi-Transport)

This sample agent can roll dice of different sizes and check if numbers are prime. This agent demonstrates
multi-transport capabilities, supporting both gRPC and JSON-RPC transport protocols. The agent is written
using Quarkus LangChain4j and makes use of the [A2A Java](https://github.com/a2aproject/a2a-java) SDK.

## Prerequisites

- Java 17 or higher
- Access to an LLM and API Key

## Running the Sample

This sample consists of an A2A server agent, which is in the `server` directory, and an A2A client,
which is in the `client` directory.

### Running the A2A Server Agent

1. Navigate to the `dice_agent_multi_transport` sample directory:

    ```bash
    cd samples/java/agents/dice_agent_multi_transport/server
    ```

2. Set your Google AI Studio API Key as an environment variable:

   ```bash
   export QUARKUS_LANGCHAIN4J_AI_GEMINI_API_KEY=your_api_key_here
   ```

   Alternatively, you can create a `.env` file in the `dice_agent_multi_transport` directory:

   ```bash
   QUARKUS_LANGCHAIN4J_AI_GEMINI_API_KEY=your_api_key_here
   ```

3. Start the A2A server agent

   **NOTE:**
   By default, the agent will start on port 11000. To override this, add the `-Dquarkus.http.port=YOUR_PORT`
   option at the end of the command below.

   ```bash
   mvn quarkus:dev
   ```

### Running the A2A Java Client

The Java `TestClient` communicates with the Dice Agent using the A2A Java SDK.

Since the A2A server agent's [preferred transport](server/src/main/java/com/samples/a2a/DiceAgentCardProducer.java) is gRPC and since our client
also [supports](client/src/main/java/com/samples/a2a/TestClient.java) gRPC, the gRPC transport will be used.

1. Make sure you have [JBang installed](https://www.jbang.dev/documentation/guide/latest/installation.html)

2. Run the client using the JBang script:
   ```bash
   cd samples/java/agents/dice_agent_multi_transport/client/src/main/java/com/samples/a2a/client
   jbang TestClientRunner.java
   ```

   Or specify a custom server URL:
   ```bash
   jbang TestClientRunner.java --server-url http://localhost:11001
   ```

   Or specify a custom message:
   ```bash
   jbang TestClientRunner.java --message "Can you roll a 12-sided die and check if the result is prime?"
   ```

### Running the A2A Python Client

You can also use a Python client to communicate with the Dice Agent using the A2A
Python SDK.

Since the A2A server agent's [preferred transport](server/src/main/java/com/samples/a2a/DiceAgentCardProducer.java) is gRPC and since our [client](client/src/main/java/com/samples/a2a/TestClient.java) also supports gRPC, the gRPC
transport will be used.

1. In a separate terminal, run the A2A client and use it to send a message to the
   agent:

    ```bash
    cd samples/python/agents/dice_agent_grpc
    uv run test_client.py
    ```

## Expected Client Output

Both the Java and Python A2A clients will:
1. Connect to the dice agent
2. Fetch the agent card
3. Automatically select gRPC as the transport to be used
4. Send the message "Can you roll a 5 sided die?"
5. Display the dice roll result from the agent

## Multi-Transport Support

This sample demonstrates multi-transport capabilities by supporting both gRPC and
JSON-RPC protocols. The A2A server agent is configured to use a unified port
(11000 by default) for both transport protocols, as specified in the
`application.properties` file with `quarkus.grpc.server.use-separate-server=false`.

You can tweak the transports supported by the server or the client to experiment
with different transport protocols.

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
