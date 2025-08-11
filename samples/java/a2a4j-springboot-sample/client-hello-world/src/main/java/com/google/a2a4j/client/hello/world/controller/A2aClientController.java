/*
 * Copyright 2024-2025 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.google.a2a4j.client.hello.world.controller;

import io.github.a2ap.core.client.A2AClient;
import io.github.a2ap.core.client.CardResolver;
import io.github.a2ap.core.client.impl.DefaultA2AClient;
import io.github.a2ap.core.client.impl.HttpCardResolver;
import io.github.a2ap.core.exception.A2AError;
import io.github.a2ap.core.model.Message;
import io.github.a2ap.core.model.MessageSendParams;
import io.github.a2ap.core.model.SendMessageResponse;
import io.github.a2ap.core.model.SendStreamingMessageResponse;
import io.github.a2ap.core.model.TextPart;
import jakarta.annotation.PostConstruct;
import java.util.List;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;

/**
 * A2A Client Controller for sending messages to an A2A server.
 * This controller handles the `/a2a/client/send` endpoint to send messages
 * in JSON-RPC format to the specified A2A server.
 * <p>
 * The server URL can be configured via the `client.a2a-server-url` property.
 */
@RestController
@RequestMapping("/a2a/client")
public class A2aClientController {

    private static final Logger log = LoggerFactory.getLogger(A2aClientController.class);
    
    /**
     * The URL of the A2A server to which this client will send messages.
     */
    @Value("${client.a2a-server-url:http://localhost:8089}")
    private String serverUrl;
    
    public A2AClient a2AClient;
    
    @PostConstruct
    public void init() {
        // init this a2a card and client
        CardResolver cardResolver = new HttpCardResolver(this.serverUrl);
        this.a2AClient = new DefaultA2AClient(cardResolver);
    }
    
    /**
     * Endpoint to send a message to the A2A server.
     * It accepts a JSON payload with the message details.
     *
     * @param message The request message details.
     * @return ResponseEntity with the status and body of the response
     * from the server.
     */
    @GetMapping("/send")
    public ResponseEntity<SendMessageResponse> sendMessage(@RequestParam String message) {
        Message messageParam = Message.builder().messageId(UUID.randomUUID().toString()).role("user").parts(List.of(TextPart.builder().text(message).build())).build();
        MessageSendParams params = MessageSendParams.builder()
                .message(messageParam)
                .build();
        try {
            SendMessageResponse response = this.a2AClient.sendMessage(params);
            return ResponseEntity.ok(response);
        } catch (A2AError a2AError) {
            log.error(a2AError.getMessage(), a2AError);
            return ResponseEntity.internalServerError().build();
        }
    }

    /**
     * Endpoint to send a stream message to the A2A server.
     * It accepts a JSON payload with the message details.
     *
     * @param message The request message details.
     * @return ResponseEntity with the status and body of the response
     * from the server.
     */
    @GetMapping(path = "/stream/send", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<SendStreamingMessageResponse>> sendStreamMessage(@RequestParam String message) {
        Message messageParam = Message.builder().messageId(UUID.randomUUID().toString()).role("user").parts(List.of(TextPart.builder().text(message).build())).build();
        MessageSendParams params = MessageSendParams.builder()
                .message(messageParam)
                .build();
        return this.a2AClient.sendMessageStream(params)
                .map(event -> ServerSentEvent.builder(event).build());
    }
}
