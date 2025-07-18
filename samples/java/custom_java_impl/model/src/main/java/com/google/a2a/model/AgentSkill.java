package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * AgentSkill defines a specific skill or capability offered by an agent
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record AgentSkill(
    /**
     * ID is the unique identifier for the skill
     */
    @JsonProperty("id") String id,
    
    /**
     * Name is the human-readable name of the skill
     */
    @JsonProperty("name") String name,
    
    /**
     * Description is an optional description of the skill
     */
    @JsonProperty("description") String description,
    
    /**
     * Tags is an optional list of tags associated with the skill for categorization
     */
    @JsonProperty("tags") List<String> tags,
    
    /**
     * Examples is an optional list of example inputs or use cases for the skill
     */
    @JsonProperty("examples") List<String> examples,
    
    /**
     * InputModes is an optional list of input modes supported by this skill
     */
    @JsonProperty("inputModes") List<String> inputModes,
    
    /**
     * OutputModes is an optional list of output modes supported by this skill
     */
    @JsonProperty("outputModes") List<String> outputModes
) {
} 