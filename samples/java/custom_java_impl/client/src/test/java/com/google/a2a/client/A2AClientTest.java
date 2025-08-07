package com.google.a2a.client;

import com.google.a2a.model.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;

import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/**
 * Unit tests for A2AClient
 */
@ExtendWith(MockitoExtension.class)
class A2AClientTest {
    
    @Mock
    private HttpClient mockHttpClient;
    
    @Mock
    private HttpResponse<String> mockResponse;
    
    private A2AClient client;
    
    @BeforeEach
    void setUp() {
        client = new A2AClient("http://localhost:8080", mockHttpClient);
    }
    
    @Test
    void testSendTask() throws Exception {
        // Mock successful response
        String responseBody = """
            {
                "jsonrpc": "2.0",
                "id": "test-request-id",
                "result": {
                    "id": "test-task-1",
                    "contextId": "test-context-1",
                    "kind": "task",
                    "status": {
                        "state": "completed",
                        "message": null,
                        "timestamp": "2023-01-01T12:00:00Z"
                    },
                    "artifacts": null,
                    "history": null,
                    "metadata": {}
                }
            }
            """;
        
        when(mockResponse.statusCode()).thenReturn(200);
        when(mockResponse.body()).thenReturn(responseBody);
        when(mockHttpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
            .thenReturn(mockResponse);
        
        // Create test parameters using new Part system
        TextPart textPart = new TextPart("Hello, world!", null);
        Message message = new Message(
            UUID.randomUUID().toString(),
            "message",
            "user",
            List.of(textPart),
            null, null, null, null
        );
        
        TaskSendParams params = new TaskSendParams(
            "test-task-1",
            null,  // sessionId
            message,
            null,  // pushNotification
            null,  // historyLength
            Map.of()  // metadata
        );
        
        // Execute test
        JSONRPCResponse response = client.sendTask(params);
        
        // Verify results
        assertNotNull(response);
        assertEquals("test-request-id", response.id());
        assertEquals("2.0", response.jsonrpc());
        assertNull(response.error());
        assertNotNull(response.result());
        
        Task task = (Task) response.result();
        assertEquals("test-task-1", task.id());
        assertEquals(TaskState.COMPLETED, task.status().state());
    }
    
    @Test
    void testSendTaskWithError() throws Exception {
        // Mock error response
        String responseBody = """
            {
                "jsonrpc": "2.0",
                "id": "test-request-id",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": null
                }
            }
            """;
        
        when(mockResponse.statusCode()).thenReturn(200);
        when(mockResponse.body()).thenReturn(responseBody);
        when(mockHttpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
            .thenReturn(mockResponse);
        
        // Create test parameters
        TextPart textPart = new TextPart("Hello, world!", null);
        Message message = new Message(
            UUID.randomUUID().toString(),
            "message",
            "user",
            List.of(textPart),
            null, null, null, null
        );
        
        TaskSendParams params = new TaskSendParams(
            "test-task-1",
            null,
            message,
            null,
            null,
            Map.of()
        );
        
        // Execute test and expect exception
        A2AClientException exception = assertThrows(A2AClientException.class, () -> {
            client.sendTask(params);
        });
        
        assertEquals("Invalid Request", exception.getMessage());
        assertEquals(Integer.valueOf(-32600), exception.getErrorCode());
    }
    
    @Test
    void testGetTask() throws Exception {
        // Mock successful response
        String responseBody = """
            {
                "jsonrpc": "2.0",
                "id": "test-request-id",
                "result": {
                    "id": "test-task-1",
                    "contextId": "test-context-1",
                    "kind": "task",
                    "status": {
                        "state": "working",
                        "message": null,
                        "timestamp": "2023-01-01T12:00:00Z"
                    },
                    "artifacts": null,
                    "history": null,
                    "metadata": {}
                }
            }
            """;
        
        when(mockResponse.statusCode()).thenReturn(200);
        when(mockResponse.body()).thenReturn(responseBody);
        when(mockHttpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
            .thenReturn(mockResponse);
        
        // Create test parameters
        TaskQueryParams params = new TaskQueryParams("test-task-1", Map.of(), null);
        
        // Execute test
        JSONRPCResponse response = client.getTask(params);
        
        // Verify results
        assertNotNull(response);
        assertEquals("test-request-id", response.id());
        assertNull(response.error());
        
        Task task = (Task) response.result();
        assertEquals("test-task-1", task.id());
        assertEquals(TaskState.WORKING, task.status().state());
    }
    
    @Test
    void testCancelTask() throws Exception {
        // Mock successful response
        String responseBody = """
            {
                "jsonrpc": "2.0",
                "id": "test-request-id",
                "result": {
                    "id": "test-task-1",
                    "contextId": "test-context-1",
                    "kind": "task",
                    "status": {
                        "state": "canceled",
                        "message": null,
                        "timestamp": "2023-01-01T12:00:00Z"
                    },
                    "artifacts": null,
                    "history": null,
                    "metadata": {}
                }
            }
            """;
        
        when(mockResponse.statusCode()).thenReturn(200);
        when(mockResponse.body()).thenReturn(responseBody);
        when(mockHttpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
            .thenReturn(mockResponse);
        
        // Create test parameters
        TaskIDParams params = new TaskIDParams("test-task-1", Map.of());
        
        // Execute test
        JSONRPCResponse response = client.cancelTask(params);
        
        // Verify results
        assertNotNull(response);
        assertEquals("test-request-id", response.id());
        assertNull(response.error());
        
        Task task = (Task) response.result();
        assertEquals("test-task-1", task.id());
        assertEquals(TaskState.CANCELED, task.status().state());
    }
    
    @Test
    void testGetAgentCard() throws Exception {
        // Mock successful response
        String responseBody = """
            {
                "name": "Test Agent",
                "description": "A test agent",
                "url": "http://localhost:8080/a2a",
                "version": "1.0.0",
                "capabilities": {
                    "streaming": true,
                    "pushNotifications": false,
                    "stateTransitionHistory": true
                },
                "skills": []
            }
            """;
        
        when(mockResponse.statusCode()).thenReturn(200);
        when(mockResponse.body()).thenReturn(responseBody);
        when(mockHttpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
            .thenReturn(mockResponse);
        
        // Execute test
        AgentCard agentCard = client.getAgentCard();
        
        // Verify results
        assertNotNull(agentCard);
        assertEquals("Test Agent", agentCard.name());
        assertEquals("A test agent", agentCard.description());
        assertEquals("http://localhost:8080/a2a", agentCard.url());
        assertEquals("1.0.0", agentCard.version());
        assertTrue(agentCard.capabilities().streaming());
        assertFalse(agentCard.capabilities().pushNotifications());
        assertTrue(agentCard.capabilities().stateTransitionHistory());
    }
    
    @Test
    void testSendTaskStreaming() throws Exception {
        // Mock streaming response
        String streamingResponseBody = """
            {"jsonrpc":"2.0","id":"test-id","result":{"id":"test-task-1","status":{"state":"working"},"final":false}}
            {"jsonrpc":"2.0","id":"test-id","result":{"id":"test-task-1","status":{"state":"completed"},"final":true}}
            """;
        
        when(mockResponse.statusCode()).thenReturn(200);
        when(mockResponse.body()).thenReturn(streamingResponseBody);
        when(mockHttpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
            .thenReturn(mockResponse);
        
        // Create test parameters
        TextPart textPart = new TextPart("Hello, world!", null);
        Message message = new Message(
            UUID.randomUUID().toString(),
            "message",
            "user",
            List.of(textPart),
            null, null, null, null
        );
        
        TaskSendParams params = new TaskSendParams(
            "test-task-1",
            null,
            message,
            null,
            null,
            Map.of()
        );
        
        // Create event listener
        CountDownLatch completeLatch = new CountDownLatch(1);
        MockStreamingEventListener listener = new MockStreamingEventListener(completeLatch);
        
        // Execute test
        CompletableFuture<Void> future = client.sendTaskStreaming(params, listener);
        
        // Wait for completion
        assertTrue(completeLatch.await(5, TimeUnit.SECONDS));
        assertFalse(future.isCompletedExceptionally());
        assertTrue(listener.isCompleted());
        assertEquals(2, listener.getEventCount());
    }
    
    @Test
    void testHttpError() throws Exception {
        // Mock HTTP error response
        when(mockResponse.statusCode()).thenReturn(500);
        when(mockResponse.body()).thenReturn("Internal Server Error");
        when(mockHttpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
            .thenReturn(mockResponse);
        
        // Create test parameters
        TaskIDParams params = new TaskIDParams("test-task-1", Map.of());
        
        // Execute test and expect exception
        A2AClientException exception = assertThrows(A2AClientException.class, () -> {
            client.cancelTask(params);
        });
        
        assertTrue(exception.getMessage().contains("HTTP 500"));
    }
    
    /**
     * Mock streaming event listener for testing
     */
    private static class MockStreamingEventListener implements StreamingEventListener {
        
        private final CountDownLatch completeLatch;
        private int eventCount = 0;
        private boolean completed = false;
        private Exception error = null;
        
        public MockStreamingEventListener(CountDownLatch completeLatch) {
            this.completeLatch = completeLatch;
        }
        
        @Override
        public void onEvent(Object event) {
            eventCount++;
        }
        
        @Override
        public void onError(Exception exception) {
            this.error = exception;
            completeLatch.countDown();
        }
        
        @Override
        public void onComplete() {
            this.completed = true;
            completeLatch.countDown();
        }
        
        public int getEventCount() {
            return eventCount;
        }
        
        public boolean isCompleted() {
            return completed;
        }
        
        public Exception getError() {
            return error;
        }
    }
} 