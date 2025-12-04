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

package com.google.a2a4j.client.hello.world;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Main application class for the A2A Client Hello World example.
 * This application demonstrates how to send a message to an A2A server.
 */
@SpringBootApplication
public class A2AClientApplication {
    /**
     * Main entry point for the A2A client application.
     *
     * @param args command line arguments
     */
    public static void main(final String[] args) {
        SpringApplication.run(A2AClientApplication.class, args);
    }
}
