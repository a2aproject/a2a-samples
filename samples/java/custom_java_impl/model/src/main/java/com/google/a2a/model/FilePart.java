package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

/**
 * FilePart represents a File segment within parts
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record FilePart(
    /**
     * Kind is the part type - file for FileParts
     */
    @JsonProperty("kind") String kind,
    
    /**
     * File is the file content either as url or bytes
     */
    @JsonProperty("file") FileContent file,
    
    /**
     * Metadata is optional metadata associated with the part
     */
    @JsonProperty("metadata") Map<String, Object> metadata
) implements Part {
    
    public FilePart(FileContent file, Map<String, Object> metadata) {
        this("file", file, metadata);
    }
    
    public FilePart(FileContent file) {
        this("file", file, null);
    }
} 