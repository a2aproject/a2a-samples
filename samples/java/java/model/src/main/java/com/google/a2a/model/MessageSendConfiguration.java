package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * MessageSendConfiguration represents configuration for the send message request
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record MessageSendConfiguration(
    /**
     * AcceptedOutputModes are the accepted output modalities by the client
     */
    @JsonProperty("acceptedOutputModes") List<String> acceptedOutputModes,
    
    /**
     * Blocking indicates if the server should treat the client as a blocking request
     */
    @JsonProperty("blocking") Boolean blocking,
    
    /**
     * HistoryLength is the number of recent messages to be retrieved
     */
    @JsonProperty("historyLength") Integer historyLength,
    
    /**
     * PushNotificationConfig is where the server should send notifications when disconnected
     */
    @JsonProperty("pushNotificationConfig") PushNotificationConfig pushNotificationConfig
) {
} 