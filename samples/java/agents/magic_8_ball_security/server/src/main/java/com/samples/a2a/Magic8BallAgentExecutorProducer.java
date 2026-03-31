package com.samples.a2a;

import io.a2a.server.agentexecution.AgentExecutor;
import io.a2a.server.agentexecution.RequestContext;
import io.a2a.server.tasks.AgentEmitter;
import io.a2a.spec.A2AError;
import io.a2a.spec.Message;
import io.a2a.spec.Part;
import io.a2a.spec.Task;
import io.a2a.spec.TaskNotCancelableError;
import io.a2a.spec.TaskState;
import io.a2a.spec.TextPart;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;
import jakarta.inject.Inject;
import java.util.List;
import java.util.UUID;

/** Producer for Magic 8 Ball agent executor. */
@ApplicationScoped
public final class Magic8BallAgentExecutorProducer {

  /** The Magic 8 Ball agent instance. */
  @Inject private Magic8BallAgent magic8BallAgent;

  /**
   * Produces the agent executor for the Magic 8 Ball agent.
   *
   * @return the configured agent executor
   */
  @Produces
  public AgentExecutor agentExecutor() {
    return new Magic8BallAgentExecutor(magic8BallAgent);
  }

  /** Magic 8 Ball agent executor implementation. */
  private static class Magic8BallAgentExecutor implements AgentExecutor {

    /** The Magic 8 Ball agent instance. */
    private final Magic8BallAgent agent;

    /**
     * Constructor for Magic8BallAgentExecutor.
     *
     * @param magic8BallAgentInstance the Magic 8 Ball agent instance
     */
    Magic8BallAgentExecutor(final Magic8BallAgent magic8BallAgentInstance) {
      this.agent = magic8BallAgentInstance;
    }

    @Override
    public void execute(final RequestContext context,
                        final AgentEmitter emitter)
        throws A2AError {
      // mark the task as submitted and start working on it
      if (context.getTask() == null) {
        emitter.submit();
      }
      emitter.startWork();

      // extract the text from the message
      final String question = extractTextFromMessage(context.getMessage());

      // Generate a unique memory ID for this request for fresh chat memory
      final String memoryId = UUID.randomUUID().toString();
      System.out.println(
          "=== EXECUTOR === Using memory ID: "
                  + memoryId + " for question: " + question);

      // call the Magic 8 Ball agent with the question
      final String response = agent.answerQuestion(memoryId, question);

      // create the response part
      final TextPart responsePart = new TextPart(response);
      final List<Part<?>> parts = List.of(responsePart);

      // add the response as an artifact and complete the task
      emitter.addArtifact(parts);
      emitter.complete();
    }

    private String extractTextFromMessage(final Message message) {
      final StringBuilder textBuilder = new StringBuilder();
      if (message.parts() != null) {
        for (final Part<?> part : message.parts()) {
          if (part instanceof TextPart textPart) {
            textBuilder.append(textPart.text());
          }
        }
      }
      return textBuilder.toString();
    }

    @Override
    public void cancel(final RequestContext context,
                       final AgentEmitter emitter)
        throws A2AError {
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
