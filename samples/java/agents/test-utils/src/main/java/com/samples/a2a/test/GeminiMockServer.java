package com.samples.a2a.test;

import com.github.tomakehurst.wiremock.WireMockServer;
import com.github.tomakehurst.wiremock.client.WireMock;
import com.github.tomakehurst.wiremock.stubbing.Scenario;

import static com.github.tomakehurst.wiremock.client.WireMock.*;

/**
 * Utility class for mocking Google Gemini API responses in tests.
 * This allows testing agents without requiring real Gemini API keys.
 */
public final class GeminiMockServer {

    private GeminiMockServer() {
        // Utility class
    }

    /**
     * Configures WireMock to simulate agentic tool calling flow:
     * 1. First call returns tool call
     * 2. Second call returns text response after tool execution
     *
     * @param server the WireMock server instance
     * @param toolName the name of the tool to call
     * @param toolArgs JSON string of tool arguments
     * @param finalResponse text response after tool execution
     */
    public static void mockAgenticToolFlow(final WireMockServer server,
                                            final String toolName,
                                            final String toolArgs,
                                            final String finalResponse) {
        String scenarioName = "tool-flow-" + toolName;

        // First response: LLM decides to call tool
        server.stubFor(WireMock.post(urlPathMatching("/.*:generateContent.*"))
            .inScenario(scenarioName)
            .whenScenarioStateIs(Scenario.STARTED)
            .willReturn(aResponse()
                .withStatus(200)
                .withHeader("Content-Type", "application/json")
                .withBody(createToolCallResponse(toolName, toolArgs)))
            .willSetStateTo("tool-called"));

        // Second response: LLM responds with text after tool execution
        server.stubFor(WireMock.post(urlPathMatching("/.*:generateContent.*"))
            .inScenario(scenarioName)
            .whenScenarioStateIs("tool-called")
            .willReturn(aResponse()
                .withStatus(200)
                .withHeader("Content-Type", "application/json")
                .withBody(createTextResponse(finalResponse))));
    }

    /**
     * Configures WireMock to return a Gemini API response with text content.
     * This simulates the LLM providing a text response.
     *
     * @param server the WireMock server instance
     * @param responseText the text response from the LLM
     */
    public static void mockTextResponse(final WireMockServer server,
                                        final String responseText) {
        server.stubFor(WireMock.post(urlPathMatching("/.*:generateContent.*"))
            .willReturn(aResponse()
                .withStatus(200)
                .withHeader("Content-Type", "application/json")
                .withBody(createTextResponse(responseText))));
    }

    /**
     * Configures WireMock to return a Gemini API error response.
     *
     * @param server the WireMock server instance
     * @param statusCode HTTP status code for the error
     * @param errorMessage error message
     */
    public static void mockErrorResponse(final WireMockServer server,
                                          final int statusCode,
                                          final String errorMessage) {
        server.stubFor(WireMock.post(urlPathMatching("/.*:generateContent.*"))
            .willReturn(aResponse()
                .withStatus(statusCode)
                .withHeader("Content-Type", "application/json")
                .withBody(String.format(
                    "{\"error\":{\"message\":\"%s\",\"code\":%d}}",
                    errorMessage, statusCode))));
    }

    private static String createToolCallResponse(final String toolName,
                                                  final String toolArgs) {
        return String.format("""
            {
              "candidates": [{
                "content": {
                  "parts": [{
                    "functionCall": {
                      "name": "%s",
                      "args": %s
                    }
                  }],
                  "role": "model"
                },
                "finishReason": "STOP"
              }],
              "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 5,
                "totalTokenCount": 15
              }
            }
            """, toolName, toolArgs);
    }

    private static String createTextResponse(final String text) {
        return String.format("""
            {
              "candidates": [{
                "content": {
                  "parts": [{
                    "text": "%s"
                  }],
                  "role": "model"
                },
                "finishReason": "STOP"
              }],
              "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 20,
                "totalTokenCount": 30
              }
            }
            """, text);
    }
}
