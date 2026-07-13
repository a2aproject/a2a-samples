package com.samples.a2a;

import com.github.tomakehurst.wiremock.WireMockServer;
import com.samples.a2a.test.GeminiMockServer;
import io.quarkus.test.junit.QuarkusTest;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.junit.jupiter.api.*;

import java.io.BufferedReader;
import java.io.InputStreamReader;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Integration test that runs the JBang TestClientRunner script.
 * This tests the full A2A protocol stack: Client -> AgentExecutor -> AI Service.
 */
@QuarkusTest
public class JBangClientIntegrationTest {
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
    public void testJBangClientCanCallAgent() throws Exception {
        // Mock Gemini API with tool flow
        GeminiMockServer.mockAgenticToolFlow(
            wireMockServer,
            "rollDice",
            "{\"sides\": 6}",
            "You rolled a 6!"
        );

        // Run JBang script
        String jbangScript = "../client/src/main/java/com/samples/a2a/client/TestClientRunner.java";
        ProcessBuilder pb = new ProcessBuilder(
            "jbang",
            jbangScript,
            "--server-url", "http://localhost:" + serverPort,
            "--message", "Roll a 6-sided die"
        );
        pb.redirectErrorStream(true);
        Process process = pb.start();

        // Capture output
        StringBuilder output = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append("\n");
                System.out.println(line);
            }
        }

        // Wait for completion
        int exitCode = process.waitFor();

        // Verify success
        assertEquals(0, exitCode, "JBang script should complete successfully");
        String outputStr = output.toString();
        assertTrue(outputStr.contains("Successfully fetched public agent card"),
            "Should fetch agent card");
        assertTrue(outputStr.contains("Message sent successfully") || outputStr.contains("Final response"),
            "Should send message and receive response");
    }
}
