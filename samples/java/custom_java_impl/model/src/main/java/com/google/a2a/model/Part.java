package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonSubTypes;
import com.fasterxml.jackson.annotation.JsonTypeInfo;

/**
 * Part represents a part of a message, which can be text, a file, or structured data
 */
@JsonTypeInfo(use = JsonTypeInfo.Id.NAME, property = "kind")
@JsonSubTypes({
    @JsonSubTypes.Type(value = TextPart.class, name = "text"),
    @JsonSubTypes.Type(value = FilePart.class, name = "file"),
    @JsonSubTypes.Type(value = DataPart.class, name = "data")
})
public sealed interface Part permits TextPart, FilePart, DataPart {
} 