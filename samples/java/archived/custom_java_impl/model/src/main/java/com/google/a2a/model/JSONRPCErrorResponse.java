package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * JSONRPCErrorResponse represents a JSON-RPC 2.0 Error Response object
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record JSONRPCErrorResponse(
    /**
     * ID is the request identifier. Can be a string, number, or null.
     * Responses must have the same ID as the request they relate to.
     */
    @JsonProperty("id") Object id,
    
    /**
     * JSONRPC specifies the JSON-RPC version. Must be "2.0"
     */
    @JsonProperty("jsonrpc") String jsonrpc,
    
    /**
     * Error is the error object
     */
    @JsonProperty("error") A2AError error
) {
} 