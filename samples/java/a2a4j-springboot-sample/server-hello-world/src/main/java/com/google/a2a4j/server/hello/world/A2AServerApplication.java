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

package com.google.a2a4j.server.hello.world;

import com.google.a2a4j.server.hello.world.agent.DemoAgentExecutor;
import com.google.a2a4j.server.hello.world.controller.A2AServerController;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.reactive.config.CorsRegistry;
import org.springframework.web.reactive.config.WebFluxConfigurer;

/**
 * Main Spring Boot application class for the A2A "Hello World" server sample.
 *
 * <p>
 * This sample demonstrates a complete A2A (Agent2Agent) protocol server implementation
 * using the A2A4J Spring Boot Starter. The application provides:
 * <ul>
 * <li>Agent Card discovery endpoint at {@code /.well-known/agent.json}</li>
 * <li>JSON-RPC endpoints for synchronous and streaming communication</li>
 * <li>A demo agent executor that simulates realistic task processing</li>
 * <li>CORS configuration for cross-origin requests</li>
 * </ul>
 *
 * <p>
 * The server can be accessed at {@code http://localhost:8089} by default.
 *
 * @see DemoAgentExecutor
 * @see A2AServerController
 */

@SpringBootApplication
public class A2AServerApplication implements WebFluxConfigurer {

    /**
     * Main entry point for the A2A server application.
     *
     * @param args command line arguments
     */
    public static void main(String[] args) {
        SpringApplication.run(A2AServerApplication.class, args);
    }

    /**
     * Configures CORS (Cross-Origin Resource Sharing) settings for the WebFlux server.
     * This allows the A2A server to accept requests from any origin, which is useful for
     * development and testing scenarios.
     *
     * <p>
     * <strong>Note:</strong> In production environments, you should restrict
     * {@code allowedOrigins} to specific domains for security reasons.
     *
     * @param registry the CORS registry to configure
     */
    @Override
    public void addCorsMappings(final CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOrigins("*")
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*");
    }

}
