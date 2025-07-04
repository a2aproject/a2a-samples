package com.samples.a2a;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;
import jakarta.inject.Inject;

import java.util.List;

import io.a2a.server.agentexecution.AgentExecutor;
import io.a2a.server.agentexecution.RequestContext;
import io.a2a.server.events.EventQueue;
import io.a2a.server.tasks.TaskUpdater;
import io.a2a.spec.JSONRPCError;
import io.a2a.spec.Message;
import io.a2a.spec.Part;
import io.a2a.spec.Task;
import io.a2a.spec.TaskNotCancelableError;
import io.a2a.spec.TaskState;
import io.a2a.spec.TextPart;

@ApplicationScoped
public class ContentWriterAgentExecutorProducer {

    @Inject
    ContentWriterAgent contentWriterAgent;

    @Produces
    public AgentExecutor agentExecutor() {
        return new ContentWriterAgentExecutor(contentWriterAgent);
    }

    private static class ContentWriterAgentExecutor implements AgentExecutor {

        private final ContentWriterAgent contentWriterAgent;

        public ContentWriterAgentExecutor(ContentWriterAgent contentWriterAgent) {
            this.contentWriterAgent = contentWriterAgent;
        }

        @Override
        public void execute(RequestContext context, EventQueue eventQueue) throws JSONRPCError {
            TaskUpdater updater = new TaskUpdater(context, eventQueue);

            // mark the task as submitted and start working on it
            if (context.getTask() == null) {
                updater.submit();
            }
            updater.startWork();

            // extract the text from the message
            String assignment = extractTextFromMessage(context.getMessage());

            // call the content writer agent with the message
            String response = contentWriterAgent.writeContent(assignment);

            // create the response part
            TextPart responsePart = new TextPart(response, null);
            List<Part<?>> parts = List.of(responsePart);

            // add the response as an artifact and complete the task
            updater.addArtifact(parts, null, null, null);
            updater.complete();
        }

        private String extractTextFromMessage(Message message) {
            StringBuilder textBuilder = new StringBuilder();
            if (message.getParts() != null) {
                for (Part part : message.getParts()) {
                    if (part instanceof TextPart textPart) {
                        textBuilder.append(textPart.getText());
                    }
                }
            }
            return textBuilder.toString();
        }

        @Override
        public void cancel(RequestContext context, EventQueue eventQueue) throws JSONRPCError {
            Task task = context.getTask();

            if (task.getStatus().state() == TaskState.CANCELED) {
                // task already cancelled
                throw new TaskNotCancelableError();
            }

            if (task.getStatus().state() == TaskState.COMPLETED) {
                // task already completed
                throw new TaskNotCancelableError();
            }

            // cancel the task
            TaskUpdater updater = new TaskUpdater(context, eventQueue);
            updater.cancel();
        }
    }
}