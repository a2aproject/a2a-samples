package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

/**
 * TaskStatusUpdateEvent represents an event for task status updates
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record TaskStatusUpdateEvent(
    /**
     * ID is the ID of the task being updated
     */
    @JsonProperty("id") String id,
    
    /**
     * Status is the new status of the task
     */
    @JsonProperty("status") TaskStatus status,
    
    /**
     * Final indicates if this is the final update for the task
     */
    @JsonProperty("final") Boolean finalUpdate,
    
    /**
     * Metadata is optional metadata associated with this update event
     */
    @JsonProperty("metadata") Map<String, Object> metadata
) {
} 