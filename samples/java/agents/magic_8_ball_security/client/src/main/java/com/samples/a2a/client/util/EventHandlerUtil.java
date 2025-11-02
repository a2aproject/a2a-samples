package com.samples.a2a.client.util;

import io.a2a.client.ClientEvent;
import io.a2a.client.MessageEvent;
import io.a2a.client.TaskEvent;
import io.a2a.client.TaskUpdateEvent;
import io.a2a.spec.AgentCard;
import io.a2a.spec.Artifact;
import io.a2a.spec.Message;
import io.a2a.spec.Part;
import io.a2a.spec.TaskArtifactUpdateEvent;
import io.a2a.spec.TaskStatusUpdateEvent;
import io.a2a.spec.TextPart;
import io.a2a.spec.UpdateEvent;
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
                String text = extractTextFromArtifacts(
                        taskUpdateEvent.getTask().getArtifacts());
                messageResponse.complete(text);
              }
            } else if (updateEvent
                    instanceof
                    TaskArtifactUpdateEvent taskArtifactUpdateEvent) {
              List<Part<?>> parts = taskArtifactUpdateEvent
                      .getArtifact()
                      .parts();
              String text = extractTextFromParts(parts);
              System.out.println("Received artifact-update: " + text);
            }
          } else if (event instanceof TaskEvent taskEvent) {
            System.out.println("Received task event: "
                    + taskEvent.getTask().getId());
            if (taskEvent.getTask().getStatus().state().isFinal()) {
              String text = extractTextFromArtifacts(
                      taskEvent.getTask().getArtifacts());
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
   *
   * @param messageResponse CompletableFuture to complete exceptionally on error
   * @return error handler
   */
  public static Consumer<Throwable> createStreamingErrorHandler(
      final CompletableFuture<String> messageResponse) {
    return (error) -> {
      System.out.println("Streaming error occurred: " + error.getMessage());
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
          textBuilder.append(textPart.getText());
        }
      }
    }
    return textBuilder.toString();
  }
}
