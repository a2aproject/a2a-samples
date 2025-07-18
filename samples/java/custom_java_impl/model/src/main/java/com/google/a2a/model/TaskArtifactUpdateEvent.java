package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

/**
 * TaskArtifactUpdateEvent represents an event for task artifact updates
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record TaskArtifactUpdateEvent(
    /**
     * ID is the ID of the task being updated
     */
    @JsonProperty("id") String id,
    
    /**
     * Artifact is the new or updated artifact for the task
     */
    @JsonProperty("artifact") Artifact artifact,
    
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