package com.google.a2a.client;

import com.google.a2a.model.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

/**
 * A2A protocol client implementation
 */
public class A2AClient {

    private final String baseUrl;
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;

    /**
     * Create a new A2A client
     * 
     * @param baseUrl the base URL of the A2A server
     */
    public A2AClient(String baseUrl) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(30))
                .build();
        this.objectMapper = new ObjectMapper();
    }

    /**
     * Create a new A2A client with custom HTTP client
     * 
     * @param baseUrl the base URL of the A2A server
     * @param httpClient custom HTTP client
     */
    public A2AClient(String baseUrl, HttpClient httpClient) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.httpClient = httpClient;
        this.objectMapper = new ObjectMapper();
    }

    /**
     * Send a task message to the agent
     * 
     * @param params task send parameters
     * @return JSON-RPC response containing the task
     * @throws A2AClientException if the request fails
     */
    public JSONRPCResponse sendTask(TaskSendParams params) throws A2AClientException {
        JSONRPCRequest request = new JSONRPCRequest(
                generateRequestId(),
                "2.0",
                "message/send",
            params
        );

        return doRequest(request);
    }

    /**
     * Get the status of a task
     * 
     * @param params task query parameters
     * @return JSON-RPC response containing the task
     * @throws A2AClientException if the request fails
     */
    public JSONRPCResponse getTask(TaskQueryParams params) throws A2AClientException {
        JSONRPCRequest request = new JSONRPCRequest(
                generateRequestId(),
                "2.0",
                "tasks/get",
            params
        );

        return doRequest(request);
    }

    /**
     * Cancel a task
     * 
     * @param params task ID parameters
     * @return JSON-RPC response containing the task
     * @throws A2AClientException if the request fails
     */
    public JSONRPCResponse cancelTask(TaskIDParams params) throws A2AClientException {
        JSONRPCRequest request = new JSONRPCRequest(
                generateRequestId(),
                "2.0",
                "tasks/cancel",
            params
        );

        return doRequest(request);
    }

    /**
     * Send a task with streaming response
     * 
     * @param params task send parameters
     * @param listener event listener for streaming updates
     * @return CompletableFuture that completes when streaming ends
     */
    public CompletableFuture<Void> sendTaskStreaming(TaskSendParams params, StreamingEventListener listener) {
        return CompletableFuture.runAsync(() -> {
            try {
                JSONRPCRequest request = new JSONRPCRequest(
                        generateRequestId(),
                        "2.0",
                        "message/stream",
                        params
                    );

                String requestBody = objectMapper.writeValueAsString(request);

                HttpRequest httpRequest = HttpRequest.newBuilder()
                        .uri(URI.create(baseUrl + "/a2a/stream"))
                        .header("Content-Type", "application/json")
                        .header("Accept", "text/event-stream")
                        .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                        .build();

                HttpResponse<String> response = httpClient.send(httpRequest, HttpResponse.BodyHandlers.ofString());

                if (response.statusCode() != 200) {
                    listener.onError(new A2AClientException("HTTP " + response.statusCode() + ": " + response.body()));
                    return;
                }

                // Parse streaming response
                String[] lines = response.body().split("\n");
                StringBuilder buf = new StringBuilder();

                for (String raw : lines) {
                    String line = raw.trim();
                    if (line.isEmpty()) { // blank line = end of one SSE event
                        if (buf.length() > 0) {
                            String payload = buf.toString();
                            SendTaskStreamingResponse msg = objectMapper.readValue(payload,
                                    SendTaskStreamingResponse.class);

                            if (msg.error() != null) {
                                Integer code = msg.error().code() != null ? msg.error().code().getValue() : null;
                                listener.onError(new A2AClientException(msg.error().message(), code));
                                return;
                            }
                            if (msg.result() != null)
                                listener.onEvent(msg.result());
                            buf.setLength(0);
                        }
                        continue;
                    }

                    if (line.startsWith("data:")) {
                        buf.append(line.substring(5).trim());
                    } // ignore event:, id:, retry:
                }

                // flush tail if no trailing blank line
                if (buf.length() > 0) {
                    SendTaskStreamingResponse msg = objectMapper.readValue(buf.toString(),
                            SendTaskStreamingResponse.class);
                    if (msg.result() != null)
                        listener.onEvent(msg.result());
                }
                listener.onComplete();

            } catch (Exception e) {
                listener.onError(new A2AClientException("Streaming request failed", e));
            }
        });
    }

    /**
     * Get agent card information
     * 
     * @return the agent card
     * @throws A2AClientException if the request fails
     */
    public AgentCard getAgentCard() throws A2AClientException {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + "/.well-known/agent-card.json"))
                    .header("Accept", "application/json")
                    .GET()
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() != 200) {
                throw new A2AClientException("HTTP " + response.statusCode() + ": " + response.body());
            }

            return objectMapper.readValue(response.body(), AgentCard.class);

        } catch (IOException | InterruptedException e) {
            throw new A2AClientException("Failed to get agent card", e);
        }
    }

    /**
     * Perform HTTP request and handle response
     */
    private JSONRPCResponse doRequest(JSONRPCRequest request) throws A2AClientException {
        try {
            String requestBody = objectMapper.writeValueAsString(request);

            HttpRequest httpRequest = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + "/a2a"))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                    .build();

            HttpResponse<String> response = httpClient.send(httpRequest, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() != 200) {
                throw new A2AClientException("HTTP " + response.statusCode() + ": " + response.body());
            }

            // Parse the response
            JsonNode responseNode = objectMapper.readTree(response.body());

            // Extract basic fields
            Object id = responseNode.has("id") ? responseNode.get("id").asText() : null;
            String jsonrpc = responseNode.get("jsonrpc").asText();

            // Handle error
            JSONRPCError error = null;
            if (responseNode.has("error") && !responseNode.get("error").isNull()) {
                error = objectMapper.treeToValue(responseNode.get("error"), JSONRPCError.class);
            }

            // Handle result
            Object result = null;
            if (responseNode.has("result") && !responseNode.get("result").isNull()) {
                result = objectMapper.treeToValue(responseNode.get("result"), Task.class);
            }

            JSONRPCResponse jsonrpcResponse = new JSONRPCResponse(id, jsonrpc, result, error);

            // Check for A2A errors
            if (error != null) {
                throw new A2AClientException(error.message(), error.code());
            }

            return jsonrpcResponse;

        } catch (IOException | InterruptedException e) {
            throw new A2AClientException("Request failed", e);
        }
    }

    /**
     * Generate a unique request ID
     */
    private String generateRequestId() {
        return UUID.randomUUID().toString();
    }
}