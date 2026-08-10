package com.samples.a2a;

import io.quarkus.test.InjectMock;
import io.quarkus.test.junit.QuarkusTest;
import org.a2aproject.sdk.A2A;
import org.a2aproject.sdk.client.Client;
import org.a2aproject.sdk.client.ClientEvent;
import org.a2aproject.sdk.client.MessageEvent;
import org.a2aproject.sdk.client.TaskUpdateEvent;
import org.a2aproject.sdk.client.transport.jsonrpc.JSONRPCTransport;
import org.a2aproject.sdk.client.transport.jsonrpc.JSONRPCTransportConfig;
import org.a2aproject.sdk.spec.AgentCard;
import org.a2aproject.sdk.spec.Artifact;
import org.a2aproject.sdk.spec.Part;
import org.a2aproject.sdk.spec.TaskStatusUpdateEvent;
import org.a2aproject.sdk.spec.TextPart;
import org.a2aproject.sdk.spec.UpdateEvent;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.anyString;

@QuarkusTest
class WeatherAgentTest {

    @ConfigProperty(name = "quarkus.http.test-port", defaultValue = "8081")
    int testPort;

    @InjectMock
    WeatherAgent weatherAgent;

    private String serverUrl() {
        return "http://localhost:" + testPort;
    }

    @Test
    void testAgentCard() throws Exception {
        AgentCard card = A2A.getAgentCard(serverUrl());

        assertNotNull(card);
        assertEquals("Weather Agent", card.name());
        assertNotNull(card.skills());
        assertFalse(card.skills().isEmpty());
        assertEquals("weather_search", card.skills().get(0).id());
    }

    @Test
    void testSendMessage() throws Exception {
        Mockito.when(weatherAgent.chat(anyString()))
                .thenReturn("It is sunny and 25°C in Los Angeles, CA.");

        CompletableFuture<String> responseText = new CompletableFuture<>();

        AgentCard card = A2A.getAgentCard(serverUrl());
        Client client = Client.builder(card)
                .withTransport(JSONRPCTransport.class, new JSONRPCTransportConfig())
                .addConsumer((ClientEvent event, AgentCard agentCard) -> {
                    if (event instanceof MessageEvent messageEvent) {
                        responseText.complete(extractText(messageEvent.getMessage().parts()));
                    } else if (event instanceof TaskUpdateEvent taskUpdate) {
                        UpdateEvent update = taskUpdate.getUpdateEvent();
                        if (update instanceof TaskStatusUpdateEvent statusUpdate
                                && statusUpdate.isFinal()) {
                            StringBuilder text = new StringBuilder();
                            for (Artifact artifact : taskUpdate.getTask().artifacts()) {
                                text.append(extractText(artifact.parts()));
                            }
                            responseText.complete(text.toString());
                        }
                    }
                })
                .build();

        client.sendMessage(A2A.toUserMessage("What is the weather in LA, CA?"));

        String result = responseText.get(10, TimeUnit.SECONDS);
        assertEquals("It is sunny and 25°C in Los Angeles, CA.", result);
    }

    private static String extractText(final List<Part<?>> parts) {
        StringBuilder sb = new StringBuilder();
        if (parts != null) {
            for (Part<?> part : parts) {
                if (part instanceof TextPart textPart) {
                    sb.append(textPart.text());
                }
            }
        }
        return sb.toString();
    }
}
