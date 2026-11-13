package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * TaskPushNotificationConfig represents the configuration for task-specific push notifications
 */
public record TaskPushNotificationConfig(
    /**
     * ID is the ID of the task the notification config is associated with
     */
    @JsonProperty("id") String id,
    
    /**
     * PushNotificationConfig is the push notification configuration details
     */
    @JsonProperty("pushNotificationConfig") PushNotificationConfig pushNotificationConfig
) {
} 