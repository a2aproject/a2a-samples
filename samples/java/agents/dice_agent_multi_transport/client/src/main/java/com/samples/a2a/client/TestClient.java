package com.samples.a2a.client;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.a2a.A2A;
import io.a2a.client.Client;
import io.a2a.client.ClientEvent;
import io.a2a.client.MessageEvent;
import io.a2a.client.TaskEvent;
import io.a2a.client.TaskUpdateEvent;
import io.a2a.client.config.ClientConfig;
import io.a2a.client.http.A2ACardResolver;
import io.a2a.client.transport.grpc.GrpcTransport;
import io.a2a.client.transport.grpc.GrpcTransportConfig;
import io.a2a.client.transport.jsonrpc.JSONRPCTransport;
import io.a2a.client.transport.jsonrpc.JSONRPCTransportConfig;
import io.a2a.spec.AgentCard;
import io.a2a.spec.Artifact;
import io.a2a.spec.Message;
import io.a2a.spec.Part;
import io.a2a.spec.TaskArtifactUpdateEvent;
import io.a2a.spec.TaskStatusUpdateEvent;
import io.a2a.spec.TextPart;
import io.a2a.spec.UpdateEvent;
import io.grpc.Channel;
import io.grpc.ManagedChannelBuilder;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.function.BiConsumer;
import java.util.function.Consumer;
import java.util.function.Function;

/** Creates an A2A client that sends a test message to the A2A server agent. */
public final class TestClient {

  /** The default server URL to use. */
  private static final String DEFAULT_SERVER_URL = "http://localhost:11000";

  /** The default message text to send. */
  private static final String MESSAGE_TEXT = "Can you roll a 5 sided die?";

  /** Object mapper to use. */
  private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

  private TestClient() {
      // this avoids a lint issue
  }

    /**
     * Client entry point.
     * @param args can optionally contain the --server-url and --message to use
     */
  public static void main(final String[] args) {
    String serverUrl = DEFAULT_SERVER_URL;
    String messageText = MESSAGE_TEXT;

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
      System.out.println("Connecting to dice agent at: " + serverUrl);

      // Fetch the public agent card
      AgentCard publicAgentCard =
              new A2ACardResolver(serverUrl).getAgentCard();
      System.out.println("Successfully fetched public agent card:");
      System.out.println(OBJECT_MAPPER.writeValueAsString(publicAgentCard));
      System.out.println("Using public agent card for client initialization.");

      // Create a CompletableFuture to handle async response
      final CompletableFuture<String> messageResponse
              = new CompletableFuture<>();

      // Create consumers for handling client events
      List<BiConsumer<ClientEvent, AgentCard>> consumers
              = getConsumers(messageResponse);

      // Create error handler for streaming errors
      Consumer<Throwable> streamingErrorHandler = (error) -> {
        System.out.println("Streaming error occurred: " + error.getMessage());
        error.printStackTrace();
        messageResponse.completeExceptionally(error);
      };

      // Create channel factory for gRPC transport
      Function<String, Channel> channelFactory = agentUrl -> {
        return ManagedChannelBuilder.forTarget(agentUrl).usePlaintext().build();
      };

      ClientConfig clientConfig = new ClientConfig.Builder()
              .setAcceptedOutputModes(List.of("Text"))
              .build();

      // Create the client with both JSON-RPC and gRPC transport support.
      // The A2A server agent's preferred transport is gRPC, since the client
      // also supports gRPC, this is the transport that will get used
      Client client = Client.builder(publicAgentCard)
          .addConsumers(consumers)
          .streamingErrorHandler(streamingErrorHandler)
          .withTransport(GrpcTransport.class,
                  new GrpcTransportConfig(channelFactory))
          .withTransport(JSONRPCTransport.class,
                  new JSONRPCTransportConfig())
          .clientConfig(clientConfig)
          .build();

      // Create and send the message
      Message message = A2A.toUserMessage(messageText);

      System.out.println("Sending message: " + messageText);
      client.sendMessage(message);
      System.out.println("Message sent successfully. Waiting for response...");

      try {
        // Wait for response with timeout
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

  private static List<BiConsumer<ClientEvent, AgentCard>> getConsumers(
      final CompletableFuture<String> messageResponse) {
    List<BiConsumer<ClientEvent, AgentCard>> consumers = new ArrayList<>();
    consumers.add(
        (event, agentCard) -> {
          if (event instanceof MessageEvent messageEvent) {
            Message responseMessage = messageEvent.getMessage();
            String text = extractTextFromParts(responseMessage.getParts());
            System.out.println("Received message: " + text);
            messageResponse.complete(text);
          } else if (event instanceof TaskUpdateEvent taskUpdateEvent) {
            UpdateEvent updateEvent = taskUpdateEvent.getUpdateEvent();
            if (updateEvent
                    instanceof TaskStatusUpdateEvent taskStatusUpdateEvent) {
              System.out.println(
                  "Received status-update: "
                      + taskStatusUpdateEvent.getStatus().state().asString());
              if (taskStatusUpdateEvent.isFinal()) {
                StringBuilder textBuilder = new StringBuilder();
                List<Artifact> artifacts
                        = taskUpdateEvent.getTask().getArtifacts();
                for (Artifact artifact : artifacts) {
                  textBuilder.append(extractTextFromParts(artifact.parts()));
                }
                String text = textBuilder.toString();
                messageResponse.complete(text);
              }
            } else if (updateEvent instanceof TaskArtifactUpdateEvent
                    taskArtifactUpdateEvent) {
              List<Part<?>> parts = taskArtifactUpdateEvent
                      .getArtifact()
                      .parts();
              String text = extractTextFromParts(parts);
              System.out.println("Received artifact-update: " + text);
            }
          } else if (event instanceof TaskEvent taskEvent) {
            System.out.println("Received task event: "
                    + taskEvent.getTask().getId());
          }
        });
    return consumers;
  }

  private static String extractTextFromParts(final List<Part<?>> parts) {
    final StringBuilder textBuilder = new StringBuilder();
    if (parts != null) {
      for (final Part<?> part : parts) {
        if (part instanceof TextPart textPart) {
          textBuilder.append(textPart.getText());
        }
      }
    }
    return textBuilder.toString();
  }

  private static void printUsageAndExit() {
    System.out.println("Usage: TestClient [OPTIONS]");
    System.out.println();
    System.out.println("Options:");
    System.out.println("  --server-url URL    "
            + "The URL of the A2A server agent (default: "
            + DEFAULT_SERVER_URL + ")");
    System.out.println("  --message TEXT      "
            + "The message to send to the agent "
            + "(default: \"" + MESSAGE_TEXT + "\")");
    System.out.println("  --help, -h          "
            + "Show this help message and exit");
    System.out.println();
    System.out.println("Examples:");
    System.out.println("  TestClient --server-url http://localhost:11001");
    System.out.println("  TestClient --message "
            + "\"Can you roll a 12-sided die?\"");
    System.out.println("  TestClient --server-url http://localhost:11001 "
            + "--message \"Is 17 prime?\"");
    System.exit(0);
  }
}
