# Magic 8-Ball Security Agent

This sample agent responds to yes/no questions by consulting a Magic 8-Ball.

This sample demonstrates how to secure an A2A server with Keycloak using bearer token authentication and it shows how to configure an A2A client to specify the token when
sending requests. The agent is written using Quarkus LangChain4j and makes use of the
[A2A Java](https://github.com/a2aproject/a2a-java) SDK.

## Prerequisites

- Java 17 or higher
- Access to an LLM and API Key
- A working container runtime (Docker or [Podman](https://quarkus.io/guides/podman))

>**NOTE**: We'll be making use of Quarkus Dev Services in this sample to automatically create and configure a Keycloak instance that we'll use as our OAuth2 provider. For more details on using Podman with Quarkus, see this [guide](https://quarkus.io/guides/podman).

## Running the Sample

This sample consists of an A2A server agent, which is in the `server` directory, and an A2A client,
which is in the `client` directory.

### Running the A2A Server Agent

1. Navigate to the `magic-8-ball-security` sample directory:

    ```bash
    cd samples/java/agents/magic-8-ball-security/server
    ```

2. Set your Google AI Studio API Key as an environment variable:

   ```bash
   export QUARKUS_LANGCHAIN4J_AI_GEMINI_API_KEY=your_api_key_here
   ```

   Alternatively, you can create a `.env` file in the `magic-8-ball-security/server` directory:

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

The Java `TestClient` communicates with the Magic 8-Ball Agent using the A2A Java SDK.

The client supports specifying which transport protocol to use ("jsonrpc", "rest", or "grpc"). By default, it uses JSON-RPC.

1. Make sure you have [JBang installed](https://www.jbang.dev/documentation/jbang/latest/installation.html)

2. Run the client using the JBang script:
   ```bash
   cd samples/java/agents/magic-8-ball-security/client/src/main/java/com/samples/a2a/client
   jbang TestClientRunner.java
   ```

   Or specify a custom server URL:
   ```bash
   jbang TestClientRunner.java --server-url http://localhost:11000
   ```

   Or specify a custom message:
   ```bash
   jbang TestClientRunner.java --message "Should I refactor this code?"
   ```

   Or specify a specific transport (jsonrpc, grpc, or rest):
   ```bash
   jbang TestClientRunner.java --transport grpc
   ```

   Or combine multiple options:
   ```bash
   jbang TestClientRunner.java --server-url http://localhost:11000 --message "Will my tests pass?" --transport rest
   ```

## Expected Client Output

The Java A2A client will:
1. Connect to the Magic 8-Ball agent
2. Fetch the agent card
3. Use the specified transport (JSON-RPC by default, or as specified via --transport option)
4. Send the message "Should I deploy this code on Friday?" (or your custom message)
5. Display the Magic 8-Ball's mystical response from the agent

## Keycloak OAuth2 Authentication

This sample includes a `KeycloakOAuth2CredentialService` that implements the `CredentialService` interface from the A2A Java SDK to retrieve tokens from Keycloak
using Keycloak `AuthzClient`.

## Multi-Transport Support

This sample demonstrates multi-transport capabilities by supporting the JSON-RPC, HTTP+JSON/REST, and gRPC transports. The A2A server agent is configured to use a unified port for all three transports.

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
