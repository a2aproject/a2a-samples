package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * SetTaskPushNotificationResponse represents a response to a set task push notification request
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record SetTaskPushNotificationResponse(
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
     * Result is the result of the method invocation. Required on success.
     * Should be null or omitted if an error occurred.
     */
    @JsonProperty("result") PushNotificationConfig result,
    
    /**
     * Error is an error object if an error occurred during the request.
     * Required on failure. Should be null or omitted if the request was successful.
     */
    @JsonProperty("error") A2AError error
) {
} 