package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

/**
 * TaskQueryParams represents the parameters for querying task information
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record TaskQueryParams(
    /**
     * ID is the unique identifier of the task
     */
    @JsonProperty("id") String id,
    
    /**
     * Metadata is optional metadata to include with the operation
     */
    @JsonProperty("metadata") Map<String, Object> metadata,
    
    /**
     * HistoryLength is an optional parameter to specify how much history to retrieve
     */
    @JsonProperty("historyLength") Integer historyLength
) {
} 