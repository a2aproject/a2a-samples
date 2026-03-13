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

/** Producer for dice agent executor. */
@ApplicationScoped
public final class DiceAgentExecutorProducer {

  /** The dice agent instance. */
  @Inject private DiceAgent diceAgent;

  /**
   * Produces the agent executor for the dice agent.
   *
   * @return the configured agent executor
   */
  @Produces
  public AgentExecutor agentExecutor() {
    return new DiceAgentExecutor(diceAgent);
  }

  /** Dice agent executor implementation. */
  private static class DiceAgentExecutor implements AgentExecutor {

    /** The dice agent instance. */
    private final DiceAgent agent;

    /**
     * Constructor for DiceAgentExecutor.
     *
     * @param diceAgentInstance the dice agent instance
     */
    DiceAgentExecutor(final DiceAgent diceAgentInstance) {
      this.agent = diceAgentInstance;
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
      final String assignment = extractTextFromMessage(context.getMessage());

      // call the dice agent with the message
      final String response = agent.rollAndAnswer(assignment);

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
