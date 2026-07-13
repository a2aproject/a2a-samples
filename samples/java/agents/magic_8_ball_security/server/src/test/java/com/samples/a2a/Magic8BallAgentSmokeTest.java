package com.samples.a2a;

import com.github.tomakehurst.wiremock.WireMockServer;
import com.samples.a2a.test.GeminiMockServer;
import io.quarkus.test.junit.QuarkusTest;
import jakarta.inject.Inject;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@QuarkusTest
public class Magic8BallAgentSmokeTest {

    private static WireMockServer wireMockServer;

    @Inject
    Magic8BallAgent magic8BallAgent;

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
    public void testMagic8BallAgent() {
        GeminiMockServer.mockAgenticToolFlow(
            wireMockServer,
            "shakeMagic8Ball",
            "{\"question\": \"Will this test pass?\"}",
            "The Magic 8 Ball says: It is certain!"
        );

        String response = magic8BallAgent.answerQuestion(
            "test-memory-id",
            "Will this test pass?"
        );

        assertNotNull(response);
        assertTrue(response.length() > 0);
    }
}
