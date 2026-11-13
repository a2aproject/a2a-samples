package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * AgentCapabilities describes the capabilities of an agent
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record AgentCapabilities(
    /**
     * Streaming indicates if the agent supports streaming responses
     */
    @JsonProperty("streaming") Boolean streaming,
    
    /**
     * PushNotifications indicates if the agent supports push notification mechanisms
     */
    @JsonProperty("pushNotifications") Boolean pushNotifications,
    
    /**
     * StateTransitionHistory indicates if the agent supports providing state transition history
     */
    @JsonProperty("stateTransitionHistory") Boolean stateTransitionHistory
) {
} 