package com.google.a2a.server;

import com.google.a2a.model.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

/**
 * A2AServer unit tests
 */
class A2AServerTest {
    
    private A2AServer server;
    private ObjectMapper objectMapper;
    
    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        
        // Create test agent card
        AgentCard agentCard = new AgentCard(
            "Test Agent",
            "Test Agent",
            "http://localhost:8080/a2a",
            null,
            "1.0.0",
            null,
            new AgentCapabilities(true, true, true),
            null,
            List.of("text"),
            List.of("text"),
            List.of()
        );
        
        // Create test task handler that completes tasks except for "test-task-3"
        TaskHandler taskHandler = (task, message) -> {
            TaskState targetState = TaskState.COMPLETED;
            
            // For cancel test, keep task in WORKING state
            if ("test-task-3".equals(task.id())) {
                targetState = TaskState.WORKING;
            }
            
            // Create status with appropriate state and timestamp
            TaskStatus status = new TaskStatus(
                targetState,
                null,  // No additional message
                Instant.now().toString()
            );
            
            return new Task(
                task.id(),
                task.contextId(),
                task.kind(),
                status,
                task.artifacts(),
                task.history(),
                task.metadata()
            );
        };
        
        server = new A2AServer(agentCard, taskHandler, objectMapper);
    }
    
    @Test
    void testHandleTaskSend() {
        // Create test parts using new Part interface
        TextPart textPart = new TextPart("Hello, world!", null);
        
        // Create test message with all required fields
        Message testMessage = new Message(
            UUID.randomUUID().toString(),  // messageId
            "message",                     // kind
            "user",                        // role
            List.of(textPart),            // parts
            null,                         // contextId
            null,                         // taskId
            null,                         // referenceTaskIds
            null                          // metadata
        );
        
        // Prepare test data
        Map<String, Object> params = Map.of(
            "id", "test-task-1",
            "message", Map.of(
                "messageId", testMessage.messageId(),
                "kind", testMessage.kind(),
                "role", testMessage.role(),
                "parts", List.of(Map.of(
                    "kind", "text",
                    "text", "Hello, world!"
                ))
            ),
            "metadata", Map.of()
        );
        
        JSONRPCRequest request = new JSONRPCRequest(
            "request-1",
            "2.0",
            "message/send",
            params
        );
        
        // Execute test
        JSONRPCResponse response = server.handleTaskSend(request);
        
        // Verify results
        assertNotNull(response);
        assertEquals("request-1", response.id());
        assertEquals("2.0", response.jsonrpc());
        assertNull(response.error());
        assertNotNull(response.result());
        
        Task resultTask = (Task) response.result();
        assertEquals("test-task-1", resultTask.id());
        assertEquals(TaskState.COMPLETED, resultTask.status().state());
        assertNotNull(resultTask.contextId());
        assertEquals("task", resultTask.kind());
        assertNotNull(resultTask.status().timestamp());
    }
    
    @Test
    void testHandleTaskGet() {
        // Create test message
        TextPart textPart = new TextPart("Test message", null);
        Message testMessage = new Message(
            UUID.randomUUID().toString(),
            "message",
            "user",
            List.of(textPart),
            null, null, null, null
        );
        
        // Send a task first
        Map<String, Object> sendParams = Map.of(
            "id", "test-task-2",
            "message", Map.of(
                "messageId", testMessage.messageId(),
                "kind", testMessage.kind(),
                "role", testMessage.role(),
                "parts", List.of(Map.of(
                    "kind", "text",
                    "text", "Test message"
                ))
            ),
            "metadata", Map.of()
        );
        
        JSONRPCRequest sendRequest = new JSONRPCRequest(
            "request-1",
            "2.0",
            "message/send",
            sendParams
        );
        
        server.handleTaskSend(sendRequest);
        
        // Then query the task
        Map<String, Object> getParams = Map.of("id", "test-task-2");
        JSONRPCRequest getRequest = new JSONRPCRequest(
            "request-2",
            "2.0",
            "tasks/get",
            getParams
        );
        
        // Execute test
        JSONRPCResponse response = server.handleTaskGet(getRequest);
        
        // Verify results
        assertNotNull(response);
        assertEquals("request-2", response.id());
        assertNull(response.error());
        
        Task resultTask = (Task) response.result();
        assertEquals("test-task-2", resultTask.id());
        assertEquals(TaskState.COMPLETED, resultTask.status().state());
        assertNotNull(resultTask.contextId());
        assertEquals("task", resultTask.kind());
    }
    
    @Test
    void testHandleTaskCancel() {
        // Create test message
        TextPart textPart = new TextPart("Test message", null);
        Message testMessage = new Message(
            UUID.randomUUID().toString(),
            "message",
            "user",
            List.of(textPart),
            null, null, null, null
        );
        
        // Send a task first
        Map<String, Object> sendParams = Map.of(
            "id", "test-task-3",
            "message", Map.of(
                "messageId", testMessage.messageId(),
                "kind", testMessage.kind(),
                "role", testMessage.role(),
                "parts", List.of(Map.of(
                    "kind", "text",
                    "text", "Test message"
                ))
            ),
            "metadata", Map.of()
        );
        
        JSONRPCRequest sendRequest = new JSONRPCRequest(
            "request-1",
            "2.0",
            "message/send",
            sendParams
        );
        
        server.handleTaskSend(sendRequest);
        
        // Then cancel the task
        Map<String, Object> cancelParams = Map.of("id", "test-task-3");
        JSONRPCRequest cancelRequest = new JSONRPCRequest(
            "request-2",
            "2.0",
            "tasks/cancel",
            cancelParams
        );
        
        // Execute test
        JSONRPCResponse response = server.handleTaskCancel(cancelRequest);
        
        // Verify results
        assertNotNull(response);
        assertEquals("request-2", response.id());
        assertNull(response.error());
        
        Task resultTask = (Task) response.result();
        assertEquals("test-task-3", resultTask.id());
        assertEquals(TaskState.CANCELED, resultTask.status().state());
        assertNotNull(resultTask.status().timestamp());
    }
    
    @Test
    void testHandleTaskGetNotFound() {
        // Query non-existent task
        Map<String, Object> params = Map.of("id", "non-existent-task");
        JSONRPCRequest request = new JSONRPCRequest(
            "request-1",
            "2.0",
            "tasks/get",
            params
        );
        
        // Execute test
        JSONRPCResponse response = server.handleTaskGet(request);
        
        // Verify results
        assertNotNull(response);
        assertEquals("request-1", response.id());
        assertNotNull(response.error());
        assertEquals(ErrorCode.TASK_NOT_FOUND.getValue(), response.error().code());
        assertEquals("Task not found", response.error().message());
    }
    
    @Test
    void testGetAgentCard() {
        AgentCard agentCard = server.getAgentCard();
        assertNotNull(agentCard);
        assertEquals("Test Agent", agentCard.name());
    }
    
    @Test
    void testGetTaskHistory() {
        List<Message> history = server.getTaskHistory("non-existent-task");
        assertNotNull(history);
        assertTrue(history.isEmpty());
    }
} 