package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * FileContentURI represents file content as a URI
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record FileContentURI(
    /**
     * Name is the optional name of the file
     */
    @JsonProperty("name") String name,
    
    /**
     * MimeType is the optional MIME type of the file content
     */
    @JsonProperty("mimeType") String mimeType,
    
    /**
     * URI is the URI pointing to the file content
     */
    @JsonProperty("uri") String uri
) implements FileContent {
} 