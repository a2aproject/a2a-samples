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

package com.google.a2a4j.server.hello.world.agent;

import io.github.a2ap.core.model.Artifact;
import io.github.a2ap.core.model.Message;
import io.github.a2ap.core.model.RequestContext;
import io.github.a2ap.core.model.TaskArtifactUpdateEvent;
import io.github.a2ap.core.model.TaskState;
import io.github.a2ap.core.model.TaskStatus;
import io.github.a2ap.core.model.TaskStatusUpdateEvent;
import io.github.a2ap.core.model.TextPart;
import io.github.a2ap.core.server.AgentExecutor;
import io.github.a2ap.core.server.EventQueue;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * Demo implementation of {@link AgentExecutor} that simulates realistic agent behavior.
 *
 * <p>
 * This implementation demonstrates how to create an A2A agent that processes user
 * requests and generates multiple types of content. The agent simulates a complete task
 * execution workflow including:
 * <ul>
 * <li><strong>Status Updates:</strong> Progress messages during task execution</li>
 * <li><strong>Text Artifacts:</strong> Streaming text responses with chunked
 * delivery</li>
 * <li><strong>Code Artifacts:</strong> Generated code examples</li>
 * <li><strong>Summary Artifacts:</strong> Task execution summaries</li>
 * </ul>
 *
 * <p>
 * The execution follows this timeline:
 * <ol>
 * <li>Send "Starting" status (0ms)</li>
 * <li>Send "Analyzing" status (500ms)</li>
 * <li>Send "Generating" status (1500ms)</li>
 * <li>Send text response chunks (2300ms, 2600ms, 3400ms)</li>
 * <li>Send code artifact (3400ms)</li>
 * <li>Send summary artifact (3700ms)</li>
 * <li>Send completion status (3900ms)</li>
 * </ol>
 *
 * <p>
 * <strong>Usage Example:</strong> This executor will automatically be used when you send
 * a {@code message/send} or {@code message/stream} request to the A2A server. It
 * processes any text input and generates a demonstration response showing various
 * artifact types.
 *
 * @see io.github.a2ap.core.server.AgentExecutor
 * @see io.github.a2ap.core.model.TaskArtifactUpdateEvent
 * @see io.github.a2ap.core.model.TaskStatusUpdateEvent
 */
@Component
public class DemoAgentExecutor implements AgentExecutor {

    private static final Logger log = LoggerFactory.getLogger(DemoAgentExecutor.class);

    /**
     * Executes the agent's main logic for processing user requests.
     *
     * <p>
     * This method simulates a realistic agent that processes user input and generates
     * various types of responses. The execution is asynchronous and reactive, using
     * {@link Mono} to chain operations with delays that simulate processing time.
     *
     * <p>
     * The method demonstrates several key A2A concepts:
     * <ul>
     * <li><strong>Progressive Status Updates:</strong> Keeps users informed of
     * progress</li>
     * <li><strong>Chunked Content Delivery:</strong> Streams text responses in multiple
     * chunks</li>
     * <li><strong>Multiple Artifact Types:</strong> Generates text, code, and summary
     * artifacts</li>
     * <li><strong>Event Queue Management:</strong> Properly publishes events and closes
     * the queue</li>
     * </ul>
     *
     * <p>
     * <strong>Execution Flow:</strong> <pre>
     * 1. Start task → Working status
     * 2. Analyze input → Working status
     * 3. Generate response → Working status
     * 4. Stream text response (3 chunks)
     * 5. Generate code example
     * 6. Create task summary
     * 7. Mark task complete → Completed status
     * 8. Close event queue
     * </pre>
     *
     * @param context    the request context containing the task and user message
     * @param eventQueue the event queue for publishing task updates
     * @return a Mono that completes when the task execution finishes
     */
    @Override
    public Mono<Void> execute(RequestContext context, EventQueue eventQueue) {
        String taskId = context.getTask().getId();
        String contextId = context.getTask().getContextId();
        log.info("Demo agent starting execution for task: {}", taskId);

        return Mono.fromRunnable(() -> {
            // 1. Send task start status
            sendWorkingStatus(taskId, contextId, eventQueue, "Starting to process user request...");
        }).then(Mono.delay(Duration.ofMillis(500))).then(Mono.fromRunnable(() -> {
            // 2. Send analysis phase status
            sendWorkingStatus(taskId, contextId, eventQueue, "Analyzing user input...");
        })).then(Mono.delay(Duration.ofSeconds(1))).then(Mono.fromRunnable(() -> {
            // 3. Send processing progress status
            sendWorkingStatus(taskId, contextId, eventQueue, "Generating response...");
        })).then(Mono.delay(Duration.ofMillis(800))).then(Mono.fromRunnable(() -> {
            // 4. Send first text artifact (chunk)
            sendTextArtifact(taskId, contextId, eventQueue, "text-response", "AI Assistant Response",
                    "Here's my analysis of your question:\n\n", false, false);
        })).then(Mono.delay(Duration.ofMillis(300))).then(Mono.fromRunnable(() -> {
            // 5. Continue sending text artifact (chunk)
            sendTextArtifact(taskId, contextId, eventQueue, "text-response", "AI Assistant Response",
                    "Based on the information provided, I suggest the following approach:\n", true, false);
        })).then(Mono.delay(Duration.ofMillis(500))).then(Mono.fromRunnable(() -> {
            // 6. Send code artifact
            sendCodeArtifact(taskId, contextId, eventQueue);
        })).then(Mono.delay(Duration.ofMillis(400))).then(Mono.fromRunnable(() -> {
            // 7. Complete text artifact (last chunk)
            sendTextArtifact(taskId, contextId, eventQueue, "text-response", "AI Assistant Response",
                    "\n\nIf you have any questions, please feel free to ask!", true, true);
        })).then(Mono.delay(Duration.ofMillis(300))).then(Mono.fromRunnable(() -> {
            // 8. Send summary artifact
            sendSummaryArtifact(taskId, contextId, eventQueue);
        })).then(Mono.delay(Duration.ofMillis(200))).then(Mono.fromRunnable(() -> {
            // 9. Send final completion status
            sendCompletedStatus(taskId, contextId, eventQueue);
            eventQueue.close();
            log.info("Demo agent completed task: {}", taskId);
        })).then();
    }

    /**
     * Handles task cancellation requests.
     *
     * <p>
     * This method is called when a client requests to cancel a running task using the
     * {@code tasks/cancel} JSON-RPC method. In this demo implementation, it simply logs
     * the cancellation request.
     *
     * <p>
     * <strong>Note:</strong> A production implementation should:
     * <ul>
     * <li>Stop any ongoing processing for the specified task</li>
     * <li>Clean up resources (threads, connections, etc.)</li>
     * <li>Send a final status update indicating cancellation</li>
     * <li>Close the event queue for the cancelled task</li>
     * </ul>
     *
     * @param taskId the ID of the task to cancel
     * @return a Mono that completes when cancellation is processed
     */
    @Override
    public Mono<Void> cancel(String taskId) {
        log.info("Demo agent cancelling task: {}", taskId);
        // TODO: Implement cancellation logic
        return Mono.empty();
    }

    /**
     * Sends a working status update to indicate task progress.
     *
     * <p>
     * This method creates and publishes a {@link TaskStatusUpdateEvent} with state
     * {@link TaskState#WORKING} to inform clients that the task is actively being
     * processed. The status message provides context about what the agent is currently
     * doing.
     *
     * <p>
     * Working status updates are important for:
     * <ul>
     * <li>Keeping users informed during long-running tasks</li>
     * <li>Showing that the agent is responsive and making progress</li>
     * <li>Providing context about current processing phase</li>
     * </ul>
     *
     * @param taskId        the unique identifier of the task
     * @param contextId     the context identifier for request correlation
     * @param eventQueue    the event queue to publish the status update
     * @param statusMessage a human-readable message describing current progress
     */
    private void sendWorkingStatus(String taskId, String contextId, EventQueue eventQueue, String statusMessage) {
        TaskStatusUpdateEvent workingEvent = TaskStatusUpdateEvent.builder()
                .taskId(taskId)
                .contextId(contextId)
                .status(TaskStatus.builder()
                        .state(TaskState.WORKING)
                        .timestamp(String.valueOf(Instant.now().toEpochMilli()))
                        .message(createAgentMessage(statusMessage))
                        .build())
                .isFinal(false)
                .build();

        eventQueue.enqueueEvent(workingEvent);
        log.debug("Sent working status for task {}: {}", taskId, statusMessage);
    }

    /**
     * Sends a text artifact update containing a chunk of generated text.
     *
     * <p>
     * This method demonstrates how to implement streaming text responses by sending
     * multiple chunks of text content as separate artifacts. Each chunk can either start
     * a new artifact or append to an existing one.
     *
     * <p>
     * Key features demonstrated:
     * <ul>
     * <li><strong>Chunked Delivery:</strong> Breaking large responses into smaller
     * parts</li>
     * <li><strong>Append Support:</strong> Adding content to existing artifacts</li>
     * <li><strong>Metadata:</strong> Including content type and encoding information</li>
     * <li><strong>Last Chunk Flag:</strong> Indicating when streaming is complete</li>
     * </ul>
     *
     * @param taskId     the unique identifier of the task
     * @param contextId  the context identifier for request correlation
     * @param eventQueue the event queue to publish the artifact update
     * @param artifactId the unique identifier for this artifact
     * @param name       the human-readable name of the artifact
     * @param content    the text content to send
     * @param append     whether to append to existing artifact or create new one
     * @param lastChunk  whether this is the final chunk for this artifact
     */
    private void sendTextArtifact(String taskId, String contextId, EventQueue eventQueue, String artifactId,
                                  String name, String content, boolean append, boolean lastChunk) {
        Artifact artifact = Artifact.builder()
                .artifactId(artifactId)
                .name(name)
                .description("AI generated text reply")
                .parts(List.of(TextPart.builder().text(content).build()))
                .metadata(
                        Map.of("contentType", "text/plain", "encoding", "utf-8", "chunkIndex", System.currentTimeMillis()))
                .build();

        TaskArtifactUpdateEvent artifactEvent = TaskArtifactUpdateEvent.builder()
                .taskId(taskId)
                .contextId(contextId)
                .artifact(artifact)
                .append(append)
                .lastChunk(lastChunk)
                .isFinal(false)
                .metadata(Map.of("artifactType", "text"))
                .build();

        eventQueue.enqueueEvent(artifactEvent);
        log.debug("Sent text artifact for task {}: {} chars, append={}, lastChunk={}", taskId, content.length(), append,
                lastChunk);
    }

    /**
     * Sends a code artifact containing generated Java code.
     *
     * <p>
     * This method demonstrates how to generate and send code artifacts with appropriate
     * metadata for syntax highlighting and file type detection. The generated code
     * includes proper Java syntax and demonstrates basic input validation and processing
     * patterns.
     *
     * <p>
     * Code artifacts should include:
     * <ul>
     * <li><strong>Content Type:</strong> MIME type for the programming language</li>
     * <li><strong>Language Metadata:</strong> Programming language identifier</li>
     * <li><strong>Filename:</strong> Suggested filename for the code</li>
     * <li><strong>Complete Flag:</strong> Indicating the code is ready for use</li>
     * </ul>
     *
     * @param taskId     the unique identifier of the task
     * @param contextId  the context identifier for request correlation
     * @param eventQueue the event queue to publish the artifact update
     */
    private void sendCodeArtifact(String taskId, String contextId, EventQueue eventQueue) {
        String codeContent = """
                // Example code
                public class ExampleService {

                    public String processRequest(String input) {
                        if (input == null || input.trim().isEmpty()) {
                            return "Input cannot be empty";
                        }

                        // Process input
                        String processed = input.trim().toLowerCase();
                        return "Processed result: " + processed;
                    }
                }
                """;

        Artifact artifact = Artifact.builder()
                .artifactId("code-example")
                .name("Example Code")
                .description("Example Java code generated based on requirements")
                .parts(List.of(TextPart.builder().text(codeContent).build()))
                .metadata(
                        Map.of("contentType", "text/x-java-source", "language", "java", "filename", "ExampleService.java"))
                .build();

        TaskArtifactUpdateEvent artifactEvent = TaskArtifactUpdateEvent.builder()
                .taskId(taskId)
                .contextId(contextId)
                .artifact(artifact)
                .append(false)
                .lastChunk(true)
                .isFinal(false)
                .metadata(Map.of("artifactType", "code"))
                .build();

        eventQueue.enqueueEvent(artifactEvent);
        log.debug("Sent code artifact for task {}", taskId);
    }

    /**
     * Sends a summary artifact containing task execution details.
     *
     * <p>
     * This method generates a markdown-formatted summary of the task execution, including
     * status of completed steps, execution time, and generated content. Summary artifacts
     * are useful for providing users with an overview of what the agent accomplished.
     *
     * <p>
     * Summary artifacts typically include:
     * <ul>
     * <li><strong>Execution Steps:</strong> List of completed operations</li>
     * <li><strong>Performance Metrics:</strong> Execution time and resource usage</li>
     * <li><strong>Content Overview:</strong> Summary of generated artifacts</li>
     * <li><strong>Status Indicators:</strong> Success/failure markers</li>
     * </ul>
     *
     * @param taskId     the unique identifier of the task
     * @param contextId  the context identifier for request correlation
     * @param eventQueue the event queue to publish the artifact update
     */
    private void sendSummaryArtifact(String taskId, String contextId, EventQueue eventQueue) {
        Artifact artifact = Artifact.builder()
                .artifactId("task-summary")
                .name("Task Summary")
                .description("Summary report of this task execution")
                .parts(List.of(TextPart.builder()
                        .text("## Task Execution Summary\n\n" + "✅ User request analysis completed\n"
                                + "✅ Text response generated\n" + "✅ Example code provided\n"
                                + "✅ Task executed successfully\n\n" + "Total execution time: ~3 seconds\n"
                                + "Generated content: Text response + Code example")
                        .build()))
                .metadata(Map.of("contentType", "text/markdown", "reportType", "summary"))
                .build();

        TaskArtifactUpdateEvent artifactEvent = TaskArtifactUpdateEvent.builder()
                .taskId(taskId)
                .contextId(contextId)
                .artifact(artifact)
                .append(false)
                .lastChunk(true)
                .isFinal(false)
                .metadata(Map.of("artifactType", "summary"))
                .build();

        eventQueue.enqueueEvent(artifactEvent);
        log.debug("Sent summary artifact for task {}", taskId);
    }

    /**
     * Sends the final completion status for the task.
     *
     * <p>
     * This method marks the task as {@link TaskState#COMPLETED} and includes metadata
     * about the execution results. The completion status should be sent as the final
     * event before closing the event queue.
     *
     * <p>
     * Completion status should include:
     * <ul>
     * <li><strong>Final State:</strong> COMPLETED, FAILED, or CANCELLED</li>
     * <li><strong>Summary Message:</strong> Human-readable completion description</li>
     * <li><strong>Execution Metadata:</strong> Performance and result metrics</li>
     * <li><strong>Final Flag:</strong> Indicating this is the last status update</li>
     * </ul>
     *
     * @param taskId     the unique identifier of the task
     * @param contextId  the context identifier for request correlation
     * @param eventQueue the event queue to publish the final status
     */
    private void sendCompletedStatus(String taskId, String contextId, EventQueue eventQueue) {
        TaskStatusUpdateEvent completedEvent = TaskStatusUpdateEvent.builder()
                .taskId(taskId)
                .contextId(contextId)
                .status(TaskStatus.builder()
                        .state(TaskState.COMPLETED)
                        .timestamp(String.valueOf(Instant.now().toEpochMilli()))
                        .message(createAgentMessage(
                                "Task completed successfully! I have generated a detailed response and example code for you."))
                        .build())
                .isFinal(true)
                .metadata(Map.of("executionTime", "3000ms", "artifactsGenerated", 4, "success", true))
                .build();

        eventQueue.enqueueEvent(completedEvent);
        log.debug("Sent completed status for task {}", taskId);
    }

    /**
     * Creates an agent message with the specified content.
     *
     * <p>
     * This utility method constructs a {@link Message} object with role "agent" and a
     * single text part containing the provided content. Agent messages are used in status
     * updates to provide human-readable information about task progress.
     *
     * @param content the text content for the message
     * @return a Message object representing an agent response
     */
    private Message createAgentMessage(String content) {
        return Message.builder()
                .messageId(java.util.UUID.randomUUID().toString())
                .role("agent")
                .parts(List.of(TextPart.builder().text(content).build()))
                .build();    }

}
