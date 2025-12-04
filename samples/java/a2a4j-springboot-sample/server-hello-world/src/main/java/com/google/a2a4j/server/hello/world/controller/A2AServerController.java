/*
 * Copyright 2024-2025 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.google.a2a4j.server.hello.world.controller;

import io.github.a2ap.core.jsonrpc.JSONRPCRequest;
import io.github.a2ap.core.jsonrpc.JSONRPCResponse;
import io.github.a2ap.core.model.AgentCard;
import io.github.a2ap.core.server.A2AServer;
import io.github.a2ap.core.server.Dispatcher;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;

/**
 * Spring Boot REST Controller that implements the A2A protocol endpoints.
 *
 * <p>
 * This controller provides the standard A2A protocol endpoints required for agent
 * discovery and communication:
 * <ul>
 * <li><strong>Agent Discovery:</strong> {@code GET /.well-known/agent.json} - Returns the
 * agent card</li>
 * <li><strong>Synchronous Communication:</strong> {@code POST /a2a/server} - JSON-RPC
 * requests with immediate response</li>
 * <li><strong>Streaming Communication:</strong> {@code POST /a2a/server} with Accept:
 * text/event-stream - Server-Sent Events</li>
 * </ul>
 *
 * <p>
 * The controller delegates JSON-RPC request processing to the {@link Dispatcher}, which
 * routes requests to appropriate handlers based on the method name.
 *
 * @see io.github.a2ap.core.server.Dispatcher
 * @see io.github.a2ap.core.jsonrpc.JSONRPCRequest
 * @see io.github.a2ap.core.model.AgentCard
 */
@RestController
public class A2AServerController {

    private final A2AServer a2aServer;

    private final Dispatcher a2aDispatch;

    /**
     * Constructs a new A2A server controller.
     *
     * @param a2aServer   the A2A server instance for accessing agent card
     * @param a2aDispatch the dispatcher for handling JSON-RPC requests
     */
    public A2AServerController(A2AServer a2aServer, Dispatcher a2aDispatch) {
        this.a2aServer = a2aServer;
        this.a2aDispatch = a2aDispatch;
    }

    /**
     * Returns the agent card for agent discovery.
     *
     * <p>
     * This endpoint is required by the A2A protocol for agent discovery. Clients can call
     * this endpoint to learn about the agent's capabilities, supported methods, and
     * metadata.
     *
     * <p>
     * <strong>Example request:</strong> <pre>GET /.well-known/agent.json</pre>
     *
     * <p>
     * <strong>Example response:</strong> <pre>
     * {
     *   "name": "A2A Java Server",
     *   "description": "A sample A2A agent implemented in Java",
     *   "version": "1.0.0",
     *   "url": "http://localhost:8089",
     *   "capabilities": {
     *     "streaming": true,
     *     "pushNotifications": false,
     *     "stateTransitionHistory": true
     *   }
     * }
     * </pre>
     *
     * @return ResponseEntity containing the agent card
     */
    @GetMapping(".well-known/agent.json")
    public ResponseEntity<AgentCard> getAgentCard() {
        AgentCard card = a2aServer.getSelfAgentCard();
        return ResponseEntity.ok(card);
    }

    /**
     * Handles synchronous A2A JSON-RPC requests.
     *
     * <p>
     * This endpoint processes JSON-RPC 2.0 requests and returns immediate responses. It
     * supports all standard A2A methods such as:
     * <ul>
     * <li>{@code message/send} - Send a message and create a task</li>
     * <li>{@code tasks/get} - Get task status</li>
     * <li>{@code tasks/cancel} - Cancel a task</li>
     * </ul>
     *
     * <p>
     * <strong>Example request:</strong> <pre>
     * POST /a2a/server
     * Content-Type: application/json
     *
     * {
     *   "jsonrpc": "2.0",
     *   "method": "message/send",
     *   "params": {
     *     "message": {
     *       "role": "user",
     *       "parts": [
     *         {
     *           "type": "text",
     *           "kind": "text",
     *           "text": "Hello, A2A!"
     *         }
     *       ]
     *     }
     *   },
     *   "id": "1"
     * }
     * </pre>
     *
     * @param request the JSON-RPC request
     * @return ResponseEntity containing the JSON-RPC response
     */
    @PostMapping(value = "/a2a/server", produces = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<JSONRPCResponse> handleA2ARequestTask(@RequestBody JSONRPCRequest request) {
        return ResponseEntity.ok(a2aDispatch.dispatch(request));
    }

    /**
     * Handles streaming A2A JSON-RPC requests using Server-Sent Events.
     *
     * <p>
     * This endpoint processes JSON-RPC 2.0 requests and returns a stream of events as the
     * task progresses. Clients receive real-time updates about task status, artifacts
     * generated, and completion status.
     *
     * <p>
     * The stream typically includes:
     * <ul>
     * <li><strong>Status Updates:</strong> Task state changes (WORKING, COMPLETED,
     * etc.)</li>
     * <li><strong>Artifact Updates:</strong> Generated content (text, code, files)</li>
     * <li><strong>Progress Updates:</strong> Task progress information</li>
     * </ul>
     *
     * <p>
     * <strong>Example request:</strong> <pre>
     * POST /a2a/server
     * Content-Type: application/json
     * Accept: text/event-stream
     *
     * {
     *   "jsonrpc": "2.0",
     *   "method": "message/stream",
     *   "params": {
     *     "message": {
     *       "role": "user",
     *       "parts": [
     *         {
     *           "type": "text",
     *           "kind": "text",
     *           "text": "Hello, streaming A2A!"
     *         }
     *       ]
     *     }
     *   },
     *   "id": "1"
     * }
     * </pre>
     *
     * <p>
     * <strong>Example response stream:</strong> <pre>
     * event: task-update
     * data: {"jsonrpc":"2.0","result":{"taskId":"abc123","status":"WORKING"},"id":"1"}
     *
     * event: task-update
     * data: {"jsonrpc":"2.0","result":{"taskId":"abc123","artifact":{"type":"text","content":"Hello!"}},"id":"1"}
     *
     * event: task-update
     * data: {"jsonrpc":"2.0","result":{"taskId":"abc123","status":"COMPLETED"},"id":"1"}
     * </pre>
     *
     * @param request the JSON-RPC request
     * @return Flux of ServerSentEvent containing JSON-RPC responses
     */
    @PostMapping(value = "/a2a/server", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<JSONRPCResponse>> handleA2ARequestTaskSubscribe(@RequestBody JSONRPCRequest request) {
        return a2aDispatch.dispatchStream(request)
                .map(event -> ServerSentEvent.<JSONRPCResponse>builder().data(event).event("task-update").build());
    }

}
