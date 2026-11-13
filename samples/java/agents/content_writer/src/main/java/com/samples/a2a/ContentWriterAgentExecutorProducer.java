package com.samples.a2a;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;
import jakarta.inject.Inject;

import java.util.List;

import org.a2aproject.sdk.server.agentexecution.AgentExecutor;
import org.a2aproject.sdk.server.agentexecution.RequestContext;
import org.a2aproject.sdk.server.tasks.AgentEmitter;
import org.a2aproject.sdk.spec.A2AError;
import org.a2aproject.sdk.spec.Message;
import org.a2aproject.sdk.spec.Part;
import org.a2aproject.sdk.spec.Task;
import org.a2aproject.sdk.spec.TaskNotCancelableError;
import org.a2aproject.sdk.spec.TaskState;
import org.a2aproject.sdk.spec.TextPart;

/**
 * Producer for Content Writer Agent Executor.
 */
@ApplicationScoped
public final class ContentWriterAgentExecutorProducer {

    /**
     * The content writer agent instance.
     */
    @Inject
    private ContentWriterAgent contentWriterAgent;

    /**
     * Creates the agent executor for the content writer agent.
     *
     * @return the agent executor
     */
    @Produces
    public AgentExecutor agentExecutor() {
        return new ContentWriterAgentExecutor(contentWriterAgent);
    }

    /**
     * Agent executor implementation for content writer.
     */
    private static class ContentWriterAgentExecutor implements AgentExecutor {

        /**
         * The content writer agent instance.
         */
        private final ContentWriterAgent agent;

        /**
         * Constructor for ContentWriterAgentExecutor.
         *
         * @param contentWriterAgent the content writer agent
         */
        ContentWriterAgentExecutor(final ContentWriterAgent contentWriterAgent) {
            this.agent = contentWriterAgent;
        }

        @Override
        public void execute(final RequestContext context,
                            final AgentEmitter emitter) throws A2AError {
            // mark the task as submitted and start working on it
            if (context.getTask() == null) {
                emitter.submit();
            }
            emitter.startWork();

            // extract the text from the message
            final String assignment = extractTextFromMessage(context.getMessage());

            // call the content writer agent with the message
            final String response = agent.writeContent(assignment);

            // create the response part
            final TextPart responsePart = new TextPart(response, null);
            final List<Part<?>> parts = List.of(responsePart);

            // add the response as an artifact and complete the task
            emitter.addArtifact(parts, null, null, null);
            emitter.complete();
        }

        private String extractTextFromMessage(final Message message) {
            final StringBuilder textBuilder = new StringBuilder();
            if (message.parts() != null) {
                for (final Part part : message.parts()) {
                    if (part instanceof TextPart textPart) {
                        textBuilder.append(textPart.text());
                    }
                }
            }
            return textBuilder.toString();
        }

        @Override
        public void cancel(final RequestContext context,
                           final AgentEmitter emitter) throws A2AError {
            final Task task = context.getTask();

            if (task.status().state() == TaskState.TASK_STATE_CANCELED) {
                // task already cancelled
                throw new TaskNotCancelableError();
            }

            if (task.status().state() == TaskState.TASK_STATE_COMPLETED) {
                // task already completed
                throw new TaskNotCancelableError();
            }

            // cancel the task
            emitter.cancel();
        }
    }
}
