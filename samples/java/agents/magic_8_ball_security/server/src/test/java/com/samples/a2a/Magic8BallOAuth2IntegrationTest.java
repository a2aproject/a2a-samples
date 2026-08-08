package com.samples.a2a;

import com.github.tomakehurst.wiremock.WireMockServer;
import com.samples.a2a.test.A2AClientTestUtils;
import com.samples.a2a.test.GeminiMockServer;
import io.a2a.A2A;
import io.a2a.client.Client;
import io.a2a.client.ClientEvent;
import io.a2a.client.config.ClientConfig;
import io.a2a.client.http.A2ACardResolver;
import io.a2a.client.transport.jsonrpc.JSONRPCTransport;
import io.a2a.client.transport.jsonrpc.JSONRPCTransportConfigBuilder;
import io.a2a.client.transport.spi.interceptors.auth.AuthInterceptor;
import io.a2a.client.transport.spi.interceptors.auth.CredentialService;
import io.a2a.spec.AgentCard;
import io.a2a.spec.Message;
import io.quarkus.test.junit.QuarkusTest;
import io.restassured.RestAssured;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.junit.jupiter.api.*;

import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.function.BiConsumer;
import java.util.function.Consumer;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Integration test for Magic 8 Ball agent with OAuth2 security.
 *
 * <p>Tests the full A2A protocol stack with OAuth2 authentication:
 * <ul>
 *   <li>Fetches agent card with OAuth2 security requirements</li>
 *   <li>Authenticates with Keycloak using client credentials flow</li>
 *   <li>Sends message to agent with Bearer token</li>
 *   <li>Verifies successful response</li>
 * </ul>
 */
@QuarkusTest
public class Magic8BallOAuth2IntegrationTest {
    private static WireMockServer wireMockServer;

    @ConfigProperty(name = "quarkus.http.test-port")
    int serverPort;

    @ConfigProperty(name = "quarkus.keycloak.devservices.port")
    int keycloakPort;

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
    public void testMagic8BallWithOAuth2Authentication() throws Exception {
        // Mock Gemini response
        GeminiMockServer.mockTextResponse(wireMockServer, "Signs point to yes");

        // Fetch agent card with OAuth2 security requirements
        String serverUrl = "http://localhost:" + serverPort;
        AgentCard agentCard = new A2ACardResolver(serverUrl).getAgentCard();

        // Verify agent card has OAuth2 security requirements
        assertNotNull(agentCard.securityRequirements(), "Agent card should have security requirements");
        assertFalse(agentCard.securityRequirements().isEmpty(), "Security requirements should not be empty");
        assertTrue(agentCard.securitySchemes().containsKey("oauth2"), "Should have oauth2 security scheme");

        // Get OAuth2 access token from Keycloak using client credentials flow
        String tokenEndpoint = "http://localhost:" + keycloakPort
            + "/realms/quarkus/protocol/openid-connect/token";

        String accessToken = RestAssured
            .given()
                .formParam("grant_type", "client_credentials")
                .formParam("client_id", "quarkus-app")
                .formParam("client_secret", "secret")
            .when()
                .post(tokenEndpoint)
            .then()
                .statusCode(200)
                .extract()
                .path("access_token");

        assertNotNull(accessToken, "Should receive access token from Keycloak");

        // Create CompletableFuture to capture async response
        CompletableFuture<String> messageResponse = new CompletableFuture<>();

        // Create event consumers
        List<BiConsumer<ClientEvent, AgentCard>> consumers = A2AClientTestUtils.createEventConsumers(messageResponse);

        // Create error handler
        Consumer<Throwable> errorHandler = error -> {
            messageResponse.completeExceptionally(error);
        };

        // Create credential service that returns the access token
        CredentialService credentialService = (securitySchemeName, clientCallContext) -> accessToken;

        // Create auth interceptor
        AuthInterceptor authInterceptor = new AuthInterceptor(credentialService);

        // Create authenticated streaming client with Bearer token
        Client client = Client.builder(agentCard)
            .addConsumers(consumers)
            .streamingErrorHandler(errorHandler)
            .withTransport(JSONRPCTransport.class,
                new JSONRPCTransportConfigBuilder()
                    .addInterceptor(authInterceptor)
                    .build())
            .clientConfig(new ClientConfig.Builder().build())
            .build();

        // Send message
        Message message = A2A.toUserMessage("Will this test pass?");
        client.sendMessage(message);

        // Wait for response with timeout
        String response = messageResponse.get(10, TimeUnit.SECONDS);

        assertNotNull(response, "Should have response");
        assertTrue(response.length() > 0, "Response should not be empty");
    }
}
