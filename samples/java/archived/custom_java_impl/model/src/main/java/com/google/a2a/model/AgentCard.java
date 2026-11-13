package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * AgentCard represents the metadata card for an agent
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record AgentCard(
    /**
     * Name is the name of the agent
     */
    @JsonProperty("name") String name,
    
    /**
     * Description is an optional description of the agent
     */
    @JsonProperty("description") String description,
    
    /**
     * URL is the base URL endpoint for interacting with the agent
     */
    @JsonProperty("url") String url,
    
    /**
     * Provider is information about the provider of the agent
     */
    @JsonProperty("provider") AgentProvider provider,
    
    /**
     * Version is the version identifier for the agent or its API
     */
    @JsonProperty("version") String version,
    
    /**
     * DocumentationURL is an optional URL pointing to the agent's documentation
     */
    @JsonProperty("documentationUrl") String documentationUrl,
    
    /**
     * Capabilities are the capabilities supported by the agent
     */
    @JsonProperty("capabilities") AgentCapabilities capabilities,
    
    /**
     * Authentication details required to interact with the agent
     */
    @JsonProperty("authentication") AgentAuthentication authentication,
    
    /**
     * DefaultInputModes are the default input modes supported by the agent
     */
    @JsonProperty("defaultInputModes") List<String> defaultInputModes,
    
    /**
     * DefaultOutputModes are the default output modes supported by the agent
     */
    @JsonProperty("defaultOutputModes") List<String> defaultOutputModes,
    
    /**
     * Skills is the list of specific skills offered by the agent
     */
    @JsonProperty("skills") List<AgentSkill> skills
) {
} 