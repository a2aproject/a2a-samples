package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * JSONRPCMessage represents the base interface for all JSON-RPC messages
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record JSONRPCMessage(
    /**
     * ID is the request identifier. Can be a string, number, or null.
     * Responses must have the same ID as the request they relate to.
     * Notifications (requests without an expected response) should omit the ID or use null.
     */
    @JsonProperty("id") Object id,
    
    /**
     * JSONRPC specifies the JSON-RPC version. Must be "2.0"
     */
    @JsonProperty("jsonrpc") String jsonrpc
) {
} 