package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * TaskHistory represents the history of a task
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record TaskHistory(
    /**
     * MessageHistory is the list of messages in chronological order
     */
    @JsonProperty("messageHistory") List<Message> messageHistory
) {
} 