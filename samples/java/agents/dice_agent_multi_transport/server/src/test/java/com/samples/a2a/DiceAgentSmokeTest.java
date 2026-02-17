package com.samples.a2a;

import com.github.tomakehurst.wiremock.WireMockServer;
import com.samples.a2a.test.GeminiMockServer;
import io.quarkus.test.common.QuarkusTestResource;
import io.quarkus.test.junit.QuarkusTest;
import jakarta.inject.Inject;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Smoke test for Dice Agent to verify basic functionality with mocked Gemini API.
 * This test ensures the agent works correctly after a2a-java SDK upgrades.
 */
@QuarkusTest
public class DiceAgentSmokeTest {

    private static WireMockServer wireMockServer;

    @Inject
    DiceAgent diceAgent;

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
    public void testDiceAgentCanRollDice() {
        // Mock agentic flow: tool call -> tool execution -> text response
        GeminiMockServer.mockAgenticToolFlow(
            wireMockServer,
            "rollDice",
            "{\"sides\": 6}",
            "You rolled a 6!"
        );

        // Call the agent
        String response = diceAgent.rollAndAnswer("Roll a 6-sided die");

        // Verify we got a response
        assertNotNull(response, "Agent should return a response");
        assertTrue(response.contains("6") || response.contains("rolled"),
            "Response should mention the dice roll");
    }

    @Test
    public void testDiceAgentCanCheckPrime() {
        // Mock agentic flow: tool call -> tool execution -> text response
        GeminiMockServer.mockAgenticToolFlow(
            wireMockServer,
            "checkPrime",
            "{\"numbers\": [7, 8, 11]}",
            "7 and 11 are prime numbers, but 8 is not."
        );

        // Call the agent
        String response = diceAgent.rollAndAnswer(
            "Are 7, 8, and 11 prime numbers?"
        );

        // Verify we got a response
        assertNotNull(response, "Agent should return a response");
        assertTrue(response.contains("prime") || response.contains("7"),
            "Response should mention prime numbers");
    }

    @Test
    public void testDiceAgentTextResponse() {
        // Mock Gemini API to return text response
        GeminiMockServer.mockTextResponse(
            wireMockServer,
            "I can help you roll dice and check prime numbers!"
        );

        // Call the agent
        String response = diceAgent.rollAndAnswer("What can you do?");

        // Verify we got the mocked response
        assertNotNull(response, "Agent should return a response");
        assertTrue(
            response.contains("roll dice") || response.contains("prime"),
            "Response should mention capabilities"
        );
    }
}
