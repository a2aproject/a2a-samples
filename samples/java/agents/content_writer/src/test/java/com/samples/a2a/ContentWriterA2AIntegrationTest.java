package com.samples.a2a;

import com.github.tomakehurst.wiremock.WireMockServer;
import com.samples.a2a.test.A2AClientTestUtils;
import com.samples.a2a.test.GeminiMockServer;
import io.a2a.A2A;
import io.a2a.client.Client;
import io.a2a.client.ClientEvent;
import io.a2a.client.MessageEvent;
import io.a2a.client.TaskUpdateEvent;
import io.a2a.client.config.ClientConfig;
import io.a2a.client.http.A2ACardResolver;
import io.a2a.client.transport.jsonrpc.JSONRPCTransport;
import io.a2a.client.transport.jsonrpc.JSONRPCTransportConfig;
import io.a2a.spec.AgentCard;
import io.a2a.spec.Artifact;
import io.a2a.spec.Message;
import io.a2a.spec.Part;
import io.a2a.spec.TaskStatusUpdateEvent;
import io.a2a.spec.TextPart;
import io.a2a.spec.UpdateEvent;
import io.quarkus.test.junit.QuarkusTest;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.junit.jupiter.api.*;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.function.BiConsumer;
import java.util.function.Consumer;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Integration test using A2A Client with streaming approach.
 * Tests the full A2A protocol stack: Client -> AgentExecutor -> AI Service.
 */
@QuarkusTest
public class ContentWriterA2AIntegrationTest {
    private static WireMockServer wireMockServer;

    @ConfigProperty(name = "quarkus.http.test-port")
    int serverPort;

    @BeforeAll
    public static void setupWireMock() {
        wireMockServer = new WireMockServer(8089);
        wireMockServer.start();
    }

    @AfterEach
    public void resetWireMock() {
        wireMockServer.resetAll();
    }

    @AfterAll
    public static void teardownWireMock() {
        if (wireMockServer != null) {
            wireMockServer.stop();
        }
    }

    @Test
    public void testContentWriterViaA2AProtocol() throws Exception {
        // Mock Gemini response
        GeminiMockServer.mockTextResponse(wireMockServer, "Here is your generated content!");

        // Fetch agent card
        String serverUrl = "http://localhost:" + serverPort;
        AgentCard agentCard = new A2ACardResolver(serverUrl).getAgentCard();

        // Create CompletableFuture to capture async response
        CompletableFuture<String> messageResponse = new CompletableFuture<>();

        // Create event consumers
        List<BiConsumer<ClientEvent, AgentCard>> consumers = A2AClientTestUtils.createEventConsumers(messageResponse);

        // Create error handler
        Consumer<Throwable> errorHandler = error -> {
            messageResponse.completeExceptionally(error);
        };

        // Create streaming client
        Client client = Client.builder(agentCard)
            .addConsumers(consumers)
            .streamingErrorHandler(errorHandler)
            .withTransport(JSONRPCTransport.class, new JSONRPCTransportConfig())
            .clientConfig(new ClientConfig.Builder().build())
            .build();

        // Send message
        Message message = A2A.toUserMessage("Write about testing");
        client.sendMessage(message);

        // Wait for response with timeout
        String response = messageResponse.get(10, TimeUnit.SECONDS);

        assertNotNull(response, "Should have response");
        assertTrue(response.length() > 0, "Response should not be empty");
    }

}
