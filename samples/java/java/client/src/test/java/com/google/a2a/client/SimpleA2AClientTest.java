package com.google.a2a.client;

import com.google.a2a.model.*;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Simple unit tests for A2AClient
 */
public class SimpleA2AClientTest {
    
    @Test
    public void testClientCreation() {
        A2AClient client = new A2AClient("http://localhost:8080");
        assertNotNull(client);
    }
    
    @Test
    public void testExceptionCreation() {
        A2AClientException exception = new A2AClientException("Test message");
        assertEquals("Test message", exception.getMessage());
        assertNull(exception.getErrorCode());
        
        A2AClientException exceptionWithCode = new A2AClientException("Test message", 123);
        assertEquals("Test message", exceptionWithCode.getMessage());
        assertEquals(Integer.valueOf(123), exceptionWithCode.getErrorCode());
    }
    
    @Test
    public void testModelClasses() {
        // Test that we can create model objects using new Part system
        TextPart textPart = new TextPart("Hello, world!", null);
        
        Message message = new Message(
            UUID.randomUUID().toString(),  // messageId
            "message",                     // kind
            "user",                        // role
            List.of(textPart),            // parts
            null,                         // contextId
            null,                         // taskId
            null,                         // referenceTaskIds
            null                          // metadata
        );
        
        assertNotNull(message);
        assertEquals("user", message.role());
        assertEquals("message", message.kind());
        assertEquals(1, message.parts().size());
        
        // Test TextPart properties
        Part part = message.parts().get(0);
        assertTrue(part instanceof TextPart);
        TextPart retrievedTextPart = (TextPart) part;
        assertEquals("text", retrievedTextPart.kind());
        assertEquals("Hello, world!", retrievedTextPart.text());
        
        TaskSendParams params = new TaskSendParams(
            "test-task-1",
            null,  // sessionId
            message,
            null,  // pushNotification
            null,  // historyLength
            Map.of()  // metadata
        );
        
        assertNotNull(params);
        assertEquals("test-task-1", params.id());
        assertEquals(message, params.message());
    }
} 