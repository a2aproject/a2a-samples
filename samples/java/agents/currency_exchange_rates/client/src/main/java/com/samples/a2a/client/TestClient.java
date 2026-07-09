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
import io.a2a.spec.TaskIdParams;
import io.a2a.spec.TaskStatusUpdateEvent;
import io.a2a.spec.TextPart;
import io.a2a.spec.UpdateEvent;
import io.grpc.Channel;
import io.grpc.ManagedChannelBuilder;

import java.io.EOFException;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.function.BiConsumer;
import java.util.function.Consumer;
import java.util.function.Function;

/**
 * Creates an A2A client that sends a test message to the A2A server agent.
 */
public final class TestClient {
  /**
   * The default server URL to use.
   */
  private static final String DEFAULT_SERVER_URL = "http://localhost:10000";

  /**
   * Object mapper to use.
   */
  private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

  private TestClient() {
    // this avoids a lint issue
  }

  /**
   * Client entry point.
   *
   * @param args is not taken into account
   */
  public static void main(final String[] args) {
    String serverUrl = DEFAULT_SERVER_URL;

    try {
      System.out.println("Connecting to currency agent at: " + serverUrl);

      // Fetch the public agent card
      AgentCard publicAgentCard =
        new A2ACardResolver(serverUrl).getAgentCard();
      System.out.printf("""
        Successfully fetched public agent card:
        %s
        Using public agent card for client initialization.%n
        """, OBJECT_MAPPER.writeValueAsString(publicAgentCard));

      ClientConfig clientConfig = new ClientConfig.Builder()
        .setAcceptedOutputModes(List.of("text"))
        .build();

      // Create and send the message without INPUT_REQUIRED
      runSingleTurnDemo(publicAgentCard, clientConfig);

      // Create and send the message with INPUT_REQUIRED
      runMultiTurnDemo(publicAgentCard, clientConfig);
    } catch (Exception e) {
      System.err.println("An error occurred: " + e.getMessage());
      e.printStackTrace();
    }
  }

  private static void runMultiTurnDemo(final AgentCard publicAgentCard,
                                       final ClientConfig clientConfig) {
    StreamingClient streamingClient1 = getStreamingClient(publicAgentCard,
      clientConfig);
    StreamingClient streamingClient2 = getStreamingClient(publicAgentCard,
      clientConfig);

    MessageResponse message1 = sendMessage(streamingClient1.client(),
      "How much is the exchange rate for 1 USD?", null, null,
      streamingClient1.messageResponse());

    // Resubscribe to a task to send additional information for this task
    streamingClient2.client().resubscribe(new TaskIdParams(message1.taskId()),
      streamingClient2.consumers(), streamingClient2.streamingErrorHandler());
    sendMessage(streamingClient2.client(), "CAD", message1.contextId(),
      message1.taskId(), streamingClient2.messageResponse());
  }

  private static void runSingleTurnDemo(final AgentCard publicAgentCard,
                                        final ClientConfig clientConfig) {
    StreamingClient streamingClient = getStreamingClient(publicAgentCard,
      clientConfig);
    sendMessage(streamingClient.client(), "how much is 10 USD in INR?",
      null, null, streamingClient.messageResponse());
  }

  private static StreamingClient getStreamingClient(
    final AgentCard publicAgentCard, final ClientConfig clientConfig) {
    // Create a CompletableFuture to handle async response
    CompletableFuture<MessageResponse> messageResponse =
      new CompletableFuture<>();

    // Create consumers for handling client events
    List<BiConsumer<ClientEvent, AgentCard>> consumers =
      getConsumers(messageResponse);

    // Create error handler for streaming errors
    Consumer<Throwable> streamingErrorHandler = error -> {
      if (!isStreamClosedError(error)) {
        System.out.printf("Streaming error occurred: %s%n", error.getMessage());
        error.printStackTrace();
        messageResponse.completeExceptionally(error);
      }
    };

    // Create channel factory
    Function<String, Channel> channelFactory =
      agentUrl -> ManagedChannelBuilder.forTarget(agentUrl)
        .usePlaintext().build();

    // Create the client with both JSON-RPC and gRPC transport support
    Client client = Client.builder(publicAgentCard)
      .addConsumers(consumers)
      .streamingErrorHandler(streamingErrorHandler)
      .withTransport(GrpcTransport.class,
        new GrpcTransportConfig(channelFactory))
      .withTransport(JSONRPCTransport.class, new JSONRPCTransportConfig())
      .clientConfig(clientConfig)
      .build();
    return new StreamingClient(messageResponse, consumers,
      streamingErrorHandler, client);
  }

  private static boolean isStreamClosedError(final Throwable throwable) {
    // Unwrap the CompletionException
    Throwable cause = throwable;

    while (cause != null) {
      if (cause instanceof EOFException) {
        return true;
      }
      if (cause instanceof IOException && cause.getMessage() != null
        && cause.getMessage().contains("cancelled")) {
        // stream is closed upon cancellation
        return true;
      }
      cause = cause.getCause();
    }
    return false;
  }

  private record StreamingClient(
    CompletableFuture<MessageResponse> messageResponse,
    List<BiConsumer<ClientEvent, AgentCard>> consumers,
    Consumer<Throwable> streamingErrorHandler, Client client) {
  }

  // Format for the response
  public record MessageResponse(String message, String contextId,
                                String taskId) {
  }

  private static MessageResponse
  sendMessage(final Client client,
              final String messageText,
              final String contextId,
              final String taskId,
              final CompletableFuture<MessageResponse> messageResponse) {
    Message message = A2A.toUserMessage(messageText);

    System.out.printf("Sending message: %s, %s, %s%n", messageText, contextId,
      taskId);
    client.sendMessage(message);
    System.out.println("Message sent successfully. Waiting for response...");

    try {
      // Wait for response with timeout
      MessageResponse responseText = messageResponse.get();
      System.out.printf("Message response: %s%n", responseText.message());
      return responseText;
    } catch (Exception e) {
      System.err.printf("Failed to get response: %s%n", e.getMessage());
      throw new RuntimeException(e);
    }
  }

  private static List<BiConsumer<ClientEvent, AgentCard>>
  getConsumers(final CompletableFuture<MessageResponse> messageResponse) {
    List<BiConsumer<ClientEvent, AgentCard>> consumers = new ArrayList<>();
    consumers.add(
      (event, agentCard) -> {
        if (event instanceof MessageEvent messageEvent) {
          Message responseMessage = messageEvent.getMessage();
          String text = extractTextFromParts(responseMessage.getParts());
          System.out.println("Received message: " + text);
          messageResponse.complete(
            new MessageResponse(text, null, null));
        } else if (event instanceof TaskUpdateEvent taskUpdateEvent) {
          UpdateEvent updateEvent = taskUpdateEvent.getUpdateEvent();
          if (updateEvent instanceof TaskStatusUpdateEvent
            taskStatusUpdateEvent) {
            System.out.println("Received status-update: "
              + taskStatusUpdateEvent.getStatus().state().asString());
            if (taskStatusUpdateEvent.isFinal()) {
              StringBuilder builder = new StringBuilder();
              List<Artifact> artifacts =
                taskUpdateEvent.getTask().getArtifacts();
              for (Artifact artifact : artifacts) {
                builder.append(extractTextFromParts(artifact.parts()));
              }
              messageResponse.complete(new MessageResponse(builder.toString(),
                taskStatusUpdateEvent.getContextId(),
                taskStatusUpdateEvent.getTaskId()));
            }
          } else if (updateEvent instanceof TaskArtifactUpdateEvent
            taskArtifactUpdateEvent) {
            List<Part<?>> parts = taskArtifactUpdateEvent.getArtifact().parts();
            String text = extractTextFromParts(parts);
            System.out.println("Received artifact-update: " + text);
          }
        } else if (event instanceof TaskEvent taskEvent) {
          System.out.println("Received task event: "
            + taskEvent.getTask().getId());
        }
      }
    );
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
}
