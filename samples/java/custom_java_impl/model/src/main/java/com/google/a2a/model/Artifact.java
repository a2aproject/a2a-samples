package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

/**
 * Artifact represents an output or intermediate file from a task
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record Artifact(
    /**
     * ArtifactId is the unique identifier for the artifact
     */
    @JsonProperty("artifactId") String artifactId,
    
    /**
     * Name is an optional name for the artifact
     */
    @JsonProperty("name") String name,
    
    /**
     * Description is an optional description of the artifact
     */
    @JsonProperty("description") String description,
    
    /**
     * Parts are the constituent parts of the artifact
     */
    @JsonProperty("parts") List<Part> parts,
    
    /**
     * Index is an optional index for ordering artifacts
     */
    @JsonProperty("index") Integer index,
    
    /**
     * Append indicates if this artifact content should append to previous content
     */
    @JsonProperty("append") Boolean append,
    
    /**
     * Metadata is optional metadata associated with the artifact
     */
    @JsonProperty("metadata") Map<String, Object> metadata,
    
    /**
     * LastChunk indicates if this is the last chunk of data for this artifact
     */
    @JsonProperty("lastChunk") Boolean lastChunk
) {
} 