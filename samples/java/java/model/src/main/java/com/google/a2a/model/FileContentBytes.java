package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * FileContentBytes represents file content as base64-encoded bytes
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record FileContentBytes(
    /**
     * Name is the optional name of the file
     */
    @JsonProperty("name") String name,
    
    /**
     * MimeType is the optional MIME type of the file content
     */
    @JsonProperty("mimeType") String mimeType,
    
    /**
     * Bytes is the file content encoded as a Base64 string
     */
    @JsonProperty("bytes") String bytes
) implements FileContent {
} 