package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

/**
 * DataPart represents a structured data segment within a message part
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record DataPart(
    /**
     * Kind is the part type - data for DataParts
     */
    @JsonProperty("kind") String kind,
    
    /**
     * Data is the structured data content
     */
    @JsonProperty("data") Map<String, Object> data,
    
    /**
     * Metadata is optional metadata associated with the part
     */
    @JsonProperty("metadata") Map<String, Object> metadata
) implements Part {
    
    public DataPart(Map<String, Object> data, Map<String, Object> metadata) {
        this("data", data, metadata);
    }
    
    public DataPart(Map<String, Object> data) {
        this("data", data, null);
    }
} 