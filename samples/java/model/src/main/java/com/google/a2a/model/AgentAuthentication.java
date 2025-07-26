package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * AgentAuthentication defines the authentication schemes and credentials for an agent
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record AgentAuthentication(
    /**
     * Schemes is a list of supported authentication schemes
     */
    @JsonProperty("schemes") List<String> schemes,
    
    /**
     * Credentials for authentication. Can be a string (e.g., token) or null if not required initially
     */
    @JsonProperty("credentials") String credentials
) {
} 