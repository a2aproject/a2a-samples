package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * AgentProvider represents the provider or organization behind an agent
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record AgentProvider(
    /**
     * Organization is the name of the organization providing the agent
     */
    @JsonProperty("organization") String organization,
    
    /**
     * URL associated with the agent provider
     */
    @JsonProperty("url") String url
) {
} 