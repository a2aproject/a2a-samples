package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

/**
 * MessageSendParams represents parameters sent by the client to the agent as a request.
 * May create, continue or restart a task.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record MessageSendParams(
    /**
     * Message is the message being sent to the server
     */
    @JsonProperty("message") Message message,
    
    /**
     * Configuration is the send message configuration
     */
    @JsonProperty("configuration") MessageSendConfiguration configuration,
    
    /**
     * Metadata is extension metadata
     */
    @JsonProperty("metadata") Map<String, Object> metadata
) {
} 