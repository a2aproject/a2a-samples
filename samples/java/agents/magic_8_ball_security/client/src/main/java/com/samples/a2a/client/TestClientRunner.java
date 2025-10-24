/// usr/bin/env jbang "$0" "$@" ; exit $?
//DEPS io.github.a2asdk:a2a-java-sdk-client:0.3.0.Final
//DEPS io.github.a2asdk:a2a-java-sdk-client-transport-jsonrpc:0.3.0.Final
//DEPS io.github.a2asdk:a2a-java-sdk-client-transport-grpc:0.3.0.Final
//DEPS io.github.a2asdk:a2a-java-sdk-client-transport-rest:0.3.0.Final
//DEPS io.github.a2asdk:a2a-java-sdk-client-transport-spi:0.3.0.Final
//DEPS com.fasterxml.jackson.core:jackson-databind:2.15.2
//DEPS io.grpc:grpc-netty-shaded:1.69.1
//DEPS org.keycloak:keycloak-authz-client:25.0.1
//SOURCES TestClient.java
//SOURCES util/KeycloakUtil.java
//SOURCES util/EventHandlerUtil.java
//SOURCES util/CachedToken.java
//SOURCES KeycloakOAuth2CredentialService.java
//FILES ../../../../../resources/keycloak.json

package com.samples.a2a.client;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.a2a.A2A;
import io.a2a.client.Client;
import io.a2a.client.http.A2ACardResolver;
import io.a2a.spec.A2AClientException;
import io.a2a.spec.AgentCard;
import io.a2a.spec.Message;
import java.util.concurrent.CompletableFuture;

/**
 * JBang script to run the A2A HTTP TestClient example with OAuth2
 * authentication. This script automatically handles the dependencies
 * and runs the client with a specified transport.
 *
 * <p>This is a self-contained script that demonstrates how to:
 *
 * <ul>
 *   <li>Connect to an A2A agent using a specific transport
 *       (gRPC, REST, or JSON-RPC) with OAuth2 authentication
 *   <li>Send messages and receive responses
 *   <li>Handle agent interactions
 * </ul>
 *
 * <p>Prerequisites:
 *
 * <ul>
 *   <li>JBang installed
 *   (see https://www.jbang.dev/documentation/guide/latest/installation.html)
 *   <li>A running Magic 8 Ball A2A server agent that supports the specified
 *       transport with OAuth2 authentication
 *   <li>A valid keycloak.json configuration file in the classpath
 *   <li>A running Keycloak server with properly configured client
 * </ul>
 *
 * <p>Usage:
 *
 * <pre>{@code
 * $ jbang TestClientRunner.java
 * }</pre>
 *
 * <p>Or with custom parameters:
 *
 * <pre>{@code
 * $ jbang TestClientRunner.java --server-url http://localhost:11001
 * $ jbang TestClientRunner.java --message "Should I refactor this code?"
 * $ jbang TestClientRunner.java --transport grpc
 * $ jbang TestClientRunner.java --server-url http://localhost:11001
 *  --message "Will my tests pass?" --transport rest
 * }</pre>
 *
 * <p>The script will:
 *
 * <ul>
 *   <li>Create the specified transport config with auth config
 *   <li>Communicate with the Magic 8 Ball A2A server agent
 *   <li>Automatically include OAuth2 Bearer tokens in all requests
 *   <li>Handle A2A protocol interactions and display responses
 * </ul>
 *
 * <p>The heavy lifting for client setup is handled by {@link TestClient}.
 */
public final class TestClientRunner {

  /** The default server URL to use. */
  private static final String DEFAULT_SERVER_URL = "http://localhost:11000";

  /** The default message text to send. */
  private static final String MESSAGE_TEXT
          = "Should I deploy this code on Friday?";

  /** The default transport to use. */
  private static final String DEFAULT_TRANSPORT = "jsonrpc";

  /** Object mapper to use. */
  private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

  private TestClientRunner() {
    // Utility class, prevent instantiation
  }

  /** Prints usage information and exits. */
  private static void printUsageAndExit() {
    System.out.println("Usage: jbang TestClientRunner.java [OPTIONS]");
    System.out.println();
    System.out.println("Options:");
    System.out.println(
        "  --server-url URL    The URL of the A2A server agent (default: "
            + DEFAULT_SERVER_URL
            + ")");
    System.out.println(
        "  --message TEXT      The message to send to the agent "
            + "(default: \""
            + MESSAGE_TEXT
            + "\")");
    System.out.println(
        "  --transport TYPE    "
                + "The transport type to use: jsonrpc, grpc, or rest "
            + "(default: "
            + DEFAULT_TRANSPORT
            + ")");
    System.out.println("  --help, -h        Show this help message and exit");
    System.out.println();
    System.out.println("Examples:");
    System.out.println("  jbang TestClientRunner.java "
            + "--server-url http://localhost:11001");
    System.out.println("  jbang TestClientRunner.java "
            + "--message \"Should I refactor this code?\"");
    System.out.println("  jbang TestClientRunner.java --transport grpc");
    System.out.println(
        "  jbang TestClientRunner.java --server-url http://localhost:11001 "
            + "--message \"Will my tests pass?\" --transport rest");
    System.exit(0);
  }

  /**
   * Client entry point.
   *
   * @param args can optionally contain the --server-url,
   *             --message, and --transport to use
   */
  public static void main(final String[] args) {
    System.out.println("=== A2A Client with OAuth2 Authentication Example ===");

    String serverUrl = DEFAULT_SERVER_URL;
    String messageText = MESSAGE_TEXT;
    String transport = DEFAULT_TRANSPORT;

    // Parse command line arguments
    for (int i = 0; i < args.length; i++) {
      switch (args[i]) {
        case "--server-url":
          if (i + 1 < args.length) {
            serverUrl = args[i + 1];
            i++;
          } else {
            System.err.println("Error: --server-url requires a value");
            printUsageAndExit();
          }
          break;
        case "--message":
          if (i + 1 < args.length) {
            messageText = args[i + 1];
            i++;
          } else {
            System.err.println("Error: --message requires a value");
            printUsageAndExit();
          }
          break;
        case "--transport":
          if (i + 1 < args.length) {
            transport = args[i + 1];
            i++;
          } else {
            System.err.println("Error: --transport requires a value");
            printUsageAndExit();
          }
          break;
        case "--help":
        case "-h":
          printUsageAndExit();
          break;
        default:
          System.err.println("Error: Unknown argument: " + args[i]);
          printUsageAndExit();
      }
    }

    try {
      System.out.println("Connecting to agent at: " + serverUrl);
      System.out.println("Using transport: " + transport);

      // Fetch the public agent card
      AgentCard publicAgentCard = new A2ACardResolver(serverUrl).getAgentCard();
      System.out.println("Successfully fetched public agent card:");
      System.out.println(OBJECT_MAPPER.writeValueAsString(publicAgentCard));
      System.out.println("Using public agent card for client initialization.");

      // Create a CompletableFuture to handle async response
      final CompletableFuture<String> messageResponse
              = new CompletableFuture<>();

      // Create the A2A client with the specified transport using TestClient
      Client client = TestClient.createClient(publicAgentCard,
              messageResponse, transport);

      // Create and send the message
      Message message = A2A.toUserMessage(messageText);

      System.out.println("Sending message: " + messageText);
      System.out.println("Using " + transport
              + " transport with OAuth2 Bearer token");
      try {
        client.sendMessage(message);
      } catch (A2AClientException e) {
        messageResponse.completeExceptionally(e);
      }
      System.out.println("Message sent successfully. Waiting for response...");

      try {
        // Wait for response
        String responseText = messageResponse.get();
        System.out.println("Final response: " + responseText);
      } catch (Exception e) {
        System.err.println("Failed to get response: " + e.getMessage());
        e.printStackTrace();
      }

    } catch (Exception e) {
      System.err.println("An error occurred: " + e.getMessage());
      e.printStackTrace();
    }
  }
}
