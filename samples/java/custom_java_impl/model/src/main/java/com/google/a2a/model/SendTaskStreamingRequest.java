package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * SendTaskStreamingRequest represents a request to send a task message and subscribe to updates
 */
public record SendTaskStreamingRequest(
    /**
     * ID is the request identifier. Can be a string, number, or null.
     * Responses must have the same ID as the request they relate to.
     * Notifications (requests without an expected response) should omit the ID or use null.
     */
    @JsonProperty("id") Object id,
    
    /**
     * JSONRPC specifies the JSON-RPC version. Must be "2.0"
     */
    @JsonProperty("jsonrpc") String jsonrpc,
    
    /**
     * Method is the name of the method to be invoked
     */
    @JsonProperty("method") String method,
    
    /**
     * Params are the parameters for the method
     */
    @JsonProperty("params") TaskSendParams params
) {
} 