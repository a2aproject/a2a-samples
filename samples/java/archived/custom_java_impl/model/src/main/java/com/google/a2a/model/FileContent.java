package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonSubTypes;
import com.fasterxml.jackson.annotation.JsonTypeInfo;

/**
 * FileContent represents either bytes or URI-based file content
 */
@JsonTypeInfo(use = JsonTypeInfo.Id.DEDUCTION)
@JsonSubTypes({
    @JsonSubTypes.Type(value = FileContentBytes.class),
    @JsonSubTypes.Type(value = FileContentURI.class)
})
public sealed interface FileContent permits FileContentBytes, FileContentURI {
} 