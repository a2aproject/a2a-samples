package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

/**
 * Message represents a single message exchanged between user and agent
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record Message(
    /**
     * MessageId is the identifier created by the message creator
     */
    @JsonProperty("messageId") String messageId,
    
    /**
     * Kind is the event type - message for Messages
     */
    @JsonProperty("kind") String kind,
    
    /**
     * Role is the message sender's role
     */
    @JsonProperty("role") String role,
    
    /**
     * Parts is the message content
     */
    @JsonProperty("parts") List<Part> parts,
    
    /**
     * ContextId is the context the message is associated with
     */
    @JsonProperty("contextId") String contextId,
    
    /**
     * TaskId is the identifier of task the message is related to
     */
    @JsonProperty("taskId") String taskId,
    
    /**
     * ReferenceTaskIds is the list of tasks referenced as context by this message
     */
    @JsonProperty("referenceTaskIds") List<String> referenceTaskIds,
    
    /**
     * Metadata is extension metadata
     */
    @JsonProperty("metadata") Map<String, Object> metadata
) {
    
    public Message(String messageId, String role, List<Part> parts) {
        this(messageId, "message", role, parts, null, null, null, null);
    }
    
    public Message(String messageId, String role, List<Part> parts, String contextId, String taskId) {
        this(messageId, "message", role, parts, contextId, taskId, null, null);
    }
} 