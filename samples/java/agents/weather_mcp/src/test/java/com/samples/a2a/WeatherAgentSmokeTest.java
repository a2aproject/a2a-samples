package com.samples.a2a;

import com.github.tomakehurst.wiremock.WireMockServer;
import com.samples.a2a.test.GeminiMockServer;
import io.quarkus.test.junit.QuarkusTest;
import jakarta.inject.Inject;
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

@QuarkusTest
public class WeatherAgentSmokeTest {
    private static WireMockServer wireMockServer;

    @Inject
    WeatherAgent agent;

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
    public void testWeatherAgent() {
        GeminiMockServer.mockTextResponse(wireMockServer, "The weather is sunny!");
        String response = agent.chat("What's the weather?");
        assertNotNull(response);
        assertTrue(response.length() > 0);
    }
}
