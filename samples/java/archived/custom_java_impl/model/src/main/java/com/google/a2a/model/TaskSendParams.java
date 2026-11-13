package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

/**
 * TaskSendParams represents the parameters for sending a task message
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record TaskSendParams(
    /**
     * ID is the unique identifier for the task being initiated or continued
     */
    @JsonProperty("id") String id,
    
    /**
     * SessionID is an optional identifier for the session this task belongs to
     */
    @JsonProperty("sessionId") String sessionId,
    
    /**
     * Message is the message content to send to the agent for processing
     */
    @JsonProperty("message") Message message,
    
    /**
     * PushNotification is optional push notification information for receiving notifications
     */
    @JsonProperty("pushNotification") PushNotificationConfig pushNotification,
    
    /**
     * HistoryLength is an optional parameter to specify how much message history to include
     */
    @JsonProperty("historyLength") Integer historyLength,
    
    /**
     * Metadata is optional metadata associated with sending this message
     */
    @JsonProperty("metadata") Map<String, Object> metadata
) {
} 