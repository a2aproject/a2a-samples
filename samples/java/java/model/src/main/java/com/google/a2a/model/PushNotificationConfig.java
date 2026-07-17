package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * PushNotificationConfig represents the configuration for push notifications
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record PushNotificationConfig(
    /**
     * URL is the endpoint where the agent should send notifications
     */
    @JsonProperty("url") String url,
    
    /**
     * Token is a token to be included in push notification requests for verification
     */
    @JsonProperty("token") String token,
    
    /**
     * Authentication is optional authentication details needed by the agent
     */
    @JsonProperty("authentication") PushNotificationAuthenticationInfo authentication
) {
} 