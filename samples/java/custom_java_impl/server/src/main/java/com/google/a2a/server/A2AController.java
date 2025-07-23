package com.google.a2a.server;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.a2a.model.A2AError;
import com.google.a2a.model.AgentCard;
import com.google.a2a.model.ErrorCode;
import com.google.a2a.model.JSONRPCError;
import com.google.a2a.model.JSONRPCRequest;
import com.google.a2a.model.JSONRPCResponse;
import com.google.a2a.model.SendTaskStreamingResponse;
import com.google.a2a.model.Task;
import com.google.a2a.model.TaskSendParams;
import com.google.a2a.model.TaskState;
import com.google.a2a.model.TaskStatus;
import com.google.a2a.model.TaskStatusUpdateEvent;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.time.Instant;
import java.util.concurrent.CompletableFuture;

/**
 * A2A REST controller for handling JSON-RPC requests
 */
@RestController
public class A2AController {

    private final A2AServer server;
    private final ObjectMapper objectMapper;

    public A2AController(A2AServer server, ObjectMapper objectMapper) {
        this.server = server;
        this.objectMapper = objectMapper;
    }

    /**
     * Handle JSON-RPC requests
     */
    @PostMapping(
            path = "/a2a",
            consumes = MediaType.APPLICATION_JSON_VALUE,
            produces = MediaType.APPLICATION_JSON_VALUE
    )
    public ResponseEntity<JSONRPCResponse> handleJsonRpcRequest(@RequestBody JSONRPCRequest request) {

        if (!"2.0".equals(request.jsonrpc())) {
            JSONRPCError error = new JSONRPCError(
                    ErrorCode.INVALID_REQUEST.getValue(),
                    "Invalid JSON-RPC version",
                    null
            );
            JSONRPCResponse response = new JSONRPCResponse(
                    request.id(),
                    "2.0",
                    null,
                    error
            );
            return ResponseEntity.badRequest().body(response);
        }

        JSONRPCResponse response = switch (request.method()) {
            case "message/send" -> server.handleTaskSend(request);
            case "tasks/get" -> server.handleTaskGet(request);
            case "tasks/cancel" -> server.handleTaskCancel(request);
            default -> {
                JSONRPCError error = new JSONRPCError(
                        ErrorCode.METHOD_NOT_FOUND.getValue(),
                        "Method not found",
                        null
                );
                yield new JSONRPCResponse(
                        request.id(),
                        "2.0",
                        null,
                        error
                );
            }
        };

        return ResponseEntity.ok(response);
    }

    /**
     * Handle streaming task requests (Server-Sent Events)
     */
    @PostMapping(
            value = "/a2a/stream",
            consumes = MediaType.APPLICATION_JSON_VALUE,
            produces = MediaType.TEXT_EVENT_STREAM_VALUE
    )
    public SseEmitter handleStreamingTask(@RequestBody JSONRPCRequest request) {

        SseEmitter emitter = new SseEmitter(Long.MAX_VALUE);

        // Process task asynchronously
        CompletableFuture.runAsync(() -> {
            try {
                if (!"message/send".equals(request.method())) {
                    sendErrorEvent(emitter, request.id(), ErrorCode.METHOD_NOT_FOUND, "Method not found");
                    return;
                }

                TaskSendParams params = parseTaskSendParams(request.params());

                // Create initial status with timestamp
                TaskStatus initialStatus = new TaskStatus(
                    TaskState.WORKING,
                    null,  // No message initially
                    Instant.now().toString()
                );

                // Send initial status update
                TaskStatusUpdateEvent initialEvent = new TaskStatusUpdateEvent(
                        params.id(),
                        initialStatus,
                        false,  // final
                        null    // metadata
                );

                SendTaskStreamingResponse initialResponse = new SendTaskStreamingResponse(
                        request.id(),
                        "2.0",
                        initialEvent,
                        null
                );

                emitter.send(SseEmitter.event()
                        .name("task-update")
                        .data(objectMapper.writeValueAsString(initialResponse)));

                // Process task
                JSONRPCResponse taskResponse = server.handleTaskSend(request);

                if (taskResponse.error() != null) {
                    sendErrorEvent(emitter, request.id(), ErrorCode.INTERNAL_ERROR, taskResponse.error().message());
                    return;
                }

                // Send final status update
                Task completedTask = (Task) taskResponse.result();
                TaskStatusUpdateEvent finalEvent = new TaskStatusUpdateEvent(
                        completedTask.id(),
                        completedTask.status(),
                        true,   // final
                        null    // metadata
                );

                SendTaskStreamingResponse finalResponse = new SendTaskStreamingResponse(
                        request.id(),
                        "2.0",
                        finalEvent,
                        null
                );

                emitter.send(SseEmitter.event()
                        .name("task-update")
                        .data(objectMapper.writeValueAsString(finalResponse)));

                emitter.complete();

            } catch (Exception e) {
                sendErrorEvent(emitter, request.id(), ErrorCode.INTERNAL_ERROR, e.getMessage());
            }
        });

        return emitter;
    }

    /**
     * Get agent card information
     */
    @GetMapping("/.well-known/agent.json")
    public ResponseEntity<AgentCard> getAgentCard() {
        return ResponseEntity.ok(server.getAgentCard());
    }

    /**
     * Parse TaskSendParams
     */
    private TaskSendParams parseTaskSendParams(Object params) throws Exception {
        return objectMapper.convertValue(params, TaskSendParams.class);
    }

    /**
     * Send error event
     */
    private void sendErrorEvent(SseEmitter emitter, Object requestId, ErrorCode code, String message) {
        try {
            A2AError error = new A2AError(code, message, null);
            SendTaskStreamingResponse errorResponse = new SendTaskStreamingResponse(
                    requestId,
                    "2.0",
                    null,
                    error
            );

            emitter.send(SseEmitter.event()
                    .name("error")
                    .data(objectMapper.writeValueAsString(errorResponse)));

            emitter.completeWithError(new RuntimeException(message));

        } catch (IOException e) {
            emitter.completeWithError(e);
        }
    }
}
