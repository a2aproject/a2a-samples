package com.samples.a2a.test;

import io.a2a.client.ClientEvent;
import io.a2a.client.MessageEvent;
import io.a2a.client.TaskUpdateEvent;
import io.a2a.spec.AgentCard;
import io.a2a.spec.Artifact;
import io.a2a.spec.Message;
import io.a2a.spec.Part;
import io.a2a.spec.TaskStatusUpdateEvent;
import io.a2a.spec.TextPart;
import io.a2a.spec.UpdateEvent;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.function.BiConsumer;

/**
 * Utility class for A2A Client integration tests.
 * Provides shared functionality for handling client events and extracting text from messages.
 */
public final class A2AClientTestUtils {

    private A2AClientTestUtils() {
        // Utility class
    }

    /**
     * Creates event consumers that handle MessageEvent and TaskUpdateEvent,
     * extracting text responses and completing the provided future.
     *
     * @param messageResponse the future to complete when a response is received
     * @return list of event consumers
     */
    public static List<BiConsumer<ClientEvent, AgentCard>> createEventConsumers(
            CompletableFuture<String> messageResponse) {
        List<BiConsumer<ClientEvent, AgentCard>> consumers = new ArrayList<>();
        consumers.add((event, agentCard) -> {
            if (event instanceof MessageEvent messageEvent) {
                Message responseMessage = messageEvent.getMessage();
                String text = extractTextFromParts(responseMessage.parts());
                if (!messageResponse.isDone()) {
                    messageResponse.complete(text);
                }
            } else if (event instanceof TaskUpdateEvent taskUpdateEvent) {
                UpdateEvent updateEvent = taskUpdateEvent.getUpdateEvent();
                if (updateEvent instanceof TaskStatusUpdateEvent taskStatusUpdateEvent) {
                    if (taskStatusUpdateEvent.isFinal()) {
                        StringBuilder textBuilder = new StringBuilder();
                        List<Artifact> artifacts = taskUpdateEvent.getTask().artifacts();
                        for (Artifact artifact : artifacts) {
                            textBuilder.append(extractTextFromParts(artifact.parts()));
                        }
                        String text = textBuilder.toString();
                        if (!messageResponse.isDone()) {
                            messageResponse.complete(text);
                        }
                    }
                }
            }
        });
        return consumers;
    }

    /**
     * Extracts text content from a list of Parts.
     *
     * @param parts the list of parts to extract text from
     * @return concatenated text from all TextParts
     */
    public static String extractTextFromParts(List<Part<?>> parts) {
        StringBuilder textBuilder = new StringBuilder();
        if (parts != null) {
            for (Part<?> part : parts) {
                if (part instanceof TextPart textPart) {
                    textBuilder.append(textPart.text());
                }
            }
        }
        return textBuilder.toString();
    }
}
