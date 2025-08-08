package com.google.a2a.server;

import com.google.a2a.model.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * A2AServer represents an A2A server instance
 */
public class A2AServer {

    private final AgentCard agentCard;
    private final TaskHandler handler;
    private final Map<String, Task> taskStore;
    private final Map<String, List<Message>> taskHistory;
    private final ObjectMapper objectMapper;

    public A2AServer(AgentCard agentCard, TaskHandler handler, ObjectMapper objectMapper) {
        this.agentCard = agentCard;
        this.handler = handler;
        this.taskStore = new ConcurrentHashMap<>();
        this.taskHistory = new ConcurrentHashMap<>();
        this.objectMapper = objectMapper;
    }

    /**
     * Handle task send request
     */
    public JSONRPCResponse handleTaskSend(JSONRPCRequest request) {
        try {
            TaskSendParams params = parseParams(request.params(), TaskSendParams.class);

            // Generate contextId if not provided
            String contextId = UUID.randomUUID().toString();

            // Create initial task status
            TaskStatus initialStatus = new TaskStatus(
                TaskState.WORKING,
                null,  // No message initially
                Instant.now().toString()  // Current timestamp
            );

            // Create new task with all required fields
            Task task = new Task(
                params.id(),
                contextId,
                "task",  // kind is always "task"
                initialStatus,
                null,    // No artifacts initially
                null,    // No history initially 
                params.metadata()  // Use metadata from params
            );

            // Process task
            Task updatedTask = handler.handle(task, params.message());

            // Store task and history
            taskStore.put(task.id(), updatedTask);
            taskHistory.computeIfAbsent(task.id(), k -> new CopyOnWriteArrayList<>())
                      .add(params.message());

            return createSuccessResponse(request.id(), updatedTask);

        } catch (Exception e) {
            return createErrorResponse(request.id(), ErrorCode.INTERNAL_ERROR, e.getMessage());
        }
    }

    /**
     * Handle task query request
     */
    public JSONRPCResponse handleTaskGet(JSONRPCRequest request) {
        try {
            TaskQueryParams params = parseParams(request.params(), TaskQueryParams.class);

            Task task = taskStore.get(params.id());
            if (task == null) {
                return createErrorResponse(request.id(), ErrorCode.TASK_NOT_FOUND, "Task not found");
            }

            // Include history if requested
            if (params.historyLength() != null && params.historyLength() > 0) {
                List<Message> history = getTaskHistory(params.id());
                int limit = Math.min(params.historyLength(), history.size());
                List<Message> limitedHistory = history.subList(Math.max(0, history.size() - limit), history.size());
                
                // Create task with history
                Task taskWithHistory = new Task(
                    task.id(),
                    task.contextId(),
                    task.kind(),
                    task.status(),
                    task.artifacts(),
                    limitedHistory,
                    task.metadata()
                );
                
                return createSuccessResponse(request.id(), taskWithHistory);
            }

            return createSuccessResponse(request.id(), task);

        } catch (Exception e) {
            return createErrorResponse(request.id(), ErrorCode.INVALID_REQUEST, "Invalid parameters");
        }
    }

    /**
     * Handle task cancel request
     */
    public JSONRPCResponse handleTaskCancel(JSONRPCRequest request) {
        try {
            TaskIDParams params = parseParams(request.params(), TaskIDParams.class);

            Task task = taskStore.get(params.id());
            if (task == null) {
                return createErrorResponse(request.id(), ErrorCode.TASK_NOT_FOUND, "Task not found");
            }

            // Check if task can be canceled
            if (task.status().state() == TaskState.COMPLETED || 
                task.status().state() == TaskState.CANCELED ||
                task.status().state() == TaskState.FAILED) {
                return createErrorResponse(request.id(), ErrorCode.TASK_NOT_CANCELABLE, "Task cannot be canceled");
            }

            // Create canceled status with timestamp
            TaskStatus canceledStatus = new TaskStatus(
                TaskState.CANCELED,
                null,  // No message
                Instant.now().toString()
            );

            // Update task status to canceled
            Task canceledTask = new Task(
                task.id(),
                task.contextId(),
                task.kind(),
                canceledStatus,
                task.artifacts(),
                task.history(),
                task.metadata()
            );
            
            taskStore.put(params.id(), canceledTask);

            return createSuccessResponse(request.id(), canceledTask);

        } catch (Exception e) {
            return createErrorResponse(request.id(), ErrorCode.INVALID_REQUEST, "Invalid parameters");
        }
    }

    /**
     * Get agent card information
     */
    public AgentCard getAgentCard() {
        return agentCard;
    }

    /**
     * Get task history
     */
    public List<Message> getTaskHistory(String taskId) {
        return taskHistory.getOrDefault(taskId, List.of());
    }

    /**
     * Parse request parameters
     */
    private <T> T parseParams(Object params, Class<T> clazz) throws Exception {
        return objectMapper.convertValue(params, clazz);
    }

    /**
     * Create success response
     */
    private JSONRPCResponse createSuccessResponse(Object id, Object result) {
        return new JSONRPCResponse(
            id,
            "2.0",
            result,
            null
        );
    }

    /**
     * Create error response
     */
    private JSONRPCResponse createErrorResponse(Object id, ErrorCode code, String message) {
        JSONRPCError error = new JSONRPCError(code.getValue(), message, null);
        return new JSONRPCResponse(
            id,
            "2.0",
            null,
            error
        );
    }
}
