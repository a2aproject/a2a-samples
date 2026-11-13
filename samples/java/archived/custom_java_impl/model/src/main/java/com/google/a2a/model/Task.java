package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

/**
 * Task represents an A2A task
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record Task(
    /**
     * ID is the unique identifier for the task
     */
    @JsonProperty("id") String id,
    
    /**
     * ContextId is the server-generated id for contextual alignment across interactions
     */
    @JsonProperty("contextId") String contextId,
    
    /**
     * Kind is the event type - task for Tasks
     */
    @JsonProperty("kind") String kind,
    
    /**
     * Status is the current status of the task
     */
    @JsonProperty("status") TaskStatus status,
    
    /**
     * Artifacts is the collection of artifacts created by the agent
     */
    @JsonProperty("artifacts") List<Artifact> artifacts,
    
    /**
     * History is the message history for the task
     */
    @JsonProperty("history") List<Message> history,
    
    /**
     * Metadata is extension metadata
     */
    @JsonProperty("metadata") Map<String, Object> metadata
) {
    
    public Task(String id, String contextId, TaskStatus status) {
        this(id, contextId, "task", status, null, null, null);
    }
    
    public Task(String id, String contextId, TaskStatus status, List<Artifact> artifacts, List<Message> history, Map<String, Object> metadata) {
        this(id, contextId, "task", status, artifacts, history, metadata);
    }
} 