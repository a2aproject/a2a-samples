package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * PushNotificationAuthenticationInfo defines authentication details for push notifications
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record PushNotificationAuthenticationInfo(
    /**
     * Schemes are the supported authentication schemes (e.g. Basic, Bearer)
     */
    @JsonProperty("schemes") List<String> schemes,
    
    /**
     * Credentials are optional credentials
     */
    @JsonProperty("credentials") String credentials
) {
} 