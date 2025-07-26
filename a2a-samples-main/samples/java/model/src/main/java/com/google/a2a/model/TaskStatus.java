package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * TaskStatus represents the status of a task
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record TaskStatus(
    /**
     * State is the current state of the task
     */
    @JsonProperty("state") TaskState state,
    
    /**
     * Message is an additional status update for the client
     */
    @JsonProperty("message") Message message,
    
    /**
     * Timestamp is the ISO 8601 datetime string when the status was recorded
     */
    @JsonProperty("timestamp") String timestamp
) {
} 