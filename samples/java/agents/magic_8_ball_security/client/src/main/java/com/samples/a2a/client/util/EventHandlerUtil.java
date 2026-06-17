package com.samples.a2a.client.util;

import org.a2aproject.sdk.client.ClientEvent;
import org.a2aproject.sdk.client.MessageEvent;
import org.a2aproject.sdk.client.TaskEvent;
import org.a2aproject.sdk.client.TaskUpdateEvent;
import org.a2aproject.sdk.spec.AgentCard;
import org.a2aproject.sdk.spec.Artifact;
import org.a2aproject.sdk.spec.Message;
import org.a2aproject.sdk.spec.Part;
import org.a2aproject.sdk.spec.TaskArtifactUpdateEvent;
import org.a2aproject.sdk.spec.TaskStatusUpdateEvent;
import org.a2aproject.sdk.spec.TextPart;
import org.a2aproject.sdk.spec.UpdateEvent;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.function.BiConsumer;
import java.util.function.Consumer;

/** Utility class for handling A2A client events and responses. */
public final class EventHandlerUtil {

  private EventHandlerUtil() {
  }

  /**
   * Creates event consumers for handling A2A client events.
   *
   * @param messageResponse CompletableFuture to complete
   * @return list of event consumers
   */
  public static List<BiConsumer<ClientEvent, AgentCard>> createEventConsumers(
      final CompletableFuture<String> messageResponse) {
    List<BiConsumer<ClientEvent, AgentCard>> consumers = new ArrayList<>();
    consumers.add(
        (event, agentCard) -> {
          if (event instanceof MessageEvent messageEvent) {
            Message responseMessage = messageEvent.getMessage();
            String text = extractTextFromParts(responseMessage.parts());
            System.out.println("Received message: " + text);
            messageResponse.complete(text);
          } else if (event instanceof TaskUpdateEvent taskUpdateEvent) {
            UpdateEvent updateEvent = taskUpdateEvent.getUpdateEvent();
            if (updateEvent
                    instanceof TaskStatusUpdateEvent taskStatusUpdateEvent) {
              System.out.println(
                  "Received status-update: "
                      + taskStatusUpdateEvent.status().state().name());
              if (taskStatusUpdateEvent.isFinal()) {
                String text = extractTextFromArtifacts(
                        taskUpdateEvent.getTask().artifacts());
                messageResponse.complete(text);
              }
            } else if (updateEvent
                    instanceof
                    TaskArtifactUpdateEvent taskArtifactUpdateEvent) {
              List<Part<?>> parts = taskArtifactUpdateEvent
                      .artifact()
                      .parts();
              String text = extractTextFromParts(parts);
              System.out.println("Received artifact-update: " + text);
            }
          } else if (event instanceof TaskEvent taskEvent) {
            System.out.println("Received task event: "
                    + taskEvent.getTask().id());
            if (taskEvent.getTask().status().state().isFinal()) {
              String text = extractTextFromArtifacts(
                      taskEvent.getTask().artifacts());
              messageResponse.complete(text);
            }
          }
        });
    return consumers;
  }

  private static String extractTextFromArtifacts(
          final List<Artifact> artifacts) {
    StringBuilder textBuilder = new StringBuilder();
    for (Artifact artifact : artifacts) {
      textBuilder.append(extractTextFromParts(artifact.parts()));
    }
    return textBuilder.toString();
  }

  /**
   * Creates a streaming error handler for A2A client.
   * Ignores expected stream cancellation errors that occur after
   * the response has already been received, and handles null errors
   * from normal stream completion.
   *
   * @param messageResponse CompletableFuture to complete exceptionally on error
   * @return error handler
   */
  public static Consumer<Throwable> createStreamingErrorHandler(
      final CompletableFuture<String> messageResponse) {
    return (error) -> {
      if (error == null || messageResponse.isDone()) {
        return;
      }
      System.err.println("Streaming error occurred: " + error.getMessage());
      error.printStackTrace();
      messageResponse.completeExceptionally(error);
    };
  }

  /**
   * Extracts text content from a list of parts.
   *
   * @param parts the parts to extract text from
   * @return concatenated text content
   */
  public static String extractTextFromParts(final List<Part<?>> parts) {
    final StringBuilder textBuilder = new StringBuilder();
    if (parts != null) {
      for (final Part<?> part : parts) {
        if (part instanceof TextPart textPart) {
          textBuilder.append(textPart.text());
        }
      }
    }
    return textBuilder.toString();
  }
}
