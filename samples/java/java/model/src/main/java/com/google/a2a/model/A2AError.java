package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * A2AError represents an error in the A2A protocol
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record A2AError(
    /**
     * Code is a number indicating the error type that occurred
     */
    @JsonProperty("code") ErrorCode code,
    
    /**
     * Message is a string providing a short description of the error
     */
    @JsonProperty("message") String message,
    
    /**
     * Data is optional additional data about the error
     */
    @JsonProperty("data") Object data
) {
} 