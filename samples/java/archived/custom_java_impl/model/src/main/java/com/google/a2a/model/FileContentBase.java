package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * FileContentBase represents the base structure for file content
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record FileContentBase(
    /**
     * Name is the optional name of the file
     */
    @JsonProperty("name") String name,
    
    /**
     * MimeType is the optional MIME type of the file content
     */
    @JsonProperty("mimeType") String mimeType
) {
} 