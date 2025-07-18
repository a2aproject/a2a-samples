package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * JSONRPCError represents a JSON-RPC error object
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record JSONRPCError(
    /**
     * Code is a number indicating the error type that occurred
     */
    @JsonProperty("code") int code,
    
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