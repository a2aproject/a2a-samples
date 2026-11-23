package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

/**
 * TaskIDParams represents the base parameters for task ID-based operations
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record TaskIDParams(
    /**
     * ID is the unique identifier of the task
     */
    @JsonProperty("id") String id,
    
    /**
     * Metadata is optional metadata to include with the operation
     */
    @JsonProperty("metadata") Map<String, Object> metadata
) {
} 