package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

/**
 * TextPart represents a text segment within parts
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record TextPart(
    /**
     * Kind is the part type - text for TextParts
     */
    @JsonProperty("kind") String kind,
    
    /**
     * Text is the text content
     */
    @JsonProperty("text") String text,
    
    /**
     * Metadata is optional metadata associated with the part
     */
    @JsonProperty("metadata") Map<String, Object> metadata
) implements Part {
    
    public TextPart(String text, Map<String, Object> metadata) {
        this("text", text, metadata);
    }
    
    public TextPart(String text) {
        this("text", text, null);
    }
} 