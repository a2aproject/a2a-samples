package com.samples.a2a.server;

import io.a2a.server.agentexecution.AgentExecutor;
import io.a2a.server.agentexecution.RequestContext;
import io.a2a.server.events.EventQueue;
import io.a2a.server.tasks.TaskUpdater;
import io.a2a.spec.JSONRPCError;
import io.a2a.spec.Message;
import io.a2a.spec.Part;
import io.a2a.spec.TaskNotCancelableError;
import io.a2a.spec.TaskState;
import io.a2a.spec.TextPart;
import io.quarkus.logging.Log;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;

import java.util.List;

/**
 * Producer for currency agent executor.
 */
@ApplicationScoped
public final class CurrencyAgentExecutorProducer {

  /**
   * The currency agent instance.
   */
  private final CurrencyAgent agent;

  /**
   * Constructor for CurrencyAgentExecutorProducer.
   *
   * @param currencyAgent the currency agent
   */
  public CurrencyAgentExecutorProducer(final CurrencyAgent currencyAgent) {
    this.agent = currencyAgent;
  }

  /**
   * The currency agent instance.
   *
   * @return the currency agent instance
   */
  public CurrencyAgent getCurrencyAgent() {
    return agent;
  }

  /**
   * Produces the agent executor for the currency agent.
   *
   * @return the configured agent executor
   */
  @Produces
  public AgentExecutor agentExecutor() {
    return new CurrencyAgentExecutor(getCurrencyAgent());
  }

  /**
   * Currency agent executor implementation.
   */
  private class CurrencyAgentExecutor implements AgentExecutor {
    /**
     * The currency agent instance.
     */
    private final CurrencyAgent agent;

    /**
     * Constructor for CurrencyAgentExecutor.
     *
     * @param currencyAgent the currency agent instance
     */
    CurrencyAgentExecutor(final CurrencyAgent currencyAgent) {
      this.agent = currencyAgent;
    }

    @Override
    public void execute(final RequestContext context,
                        final EventQueue eventQueue) throws JSONRPCError {
      executeLoop(context, eventQueue);
    }

    void executeLoop(final RequestContext context,
                     final EventQueue eventQueue) {
      var updater = new TaskUpdater(context, eventQueue);
      if (context.getTask() == null) {
        // Initial message - create task in SUBMITTED → WORKING state
        updater.submit();
        updater.startWork();

        getResponse(context, updater);
      } else {
        // Subsequent messages - add artifacts
        getResponse(context, updater);
      }
    }

    private void getResponse(final RequestContext context,
                             final TaskUpdater updater) {
      // extract the text from the message
      var message = extractTextFromMessage(context.getMessage());

      // call the currency agent with the message
      ResponseFormat response = agent.handleRequest(message);
      Log.infof("Response: %s", response);

      // create the response part
      TextPart responsePart = new TextPart(response.message(), null);
      List<Part<?>> parts = List.of(responsePart);

      // add the response as an artifact
      updater.addArtifact(parts);
      switch (response.status()) {
        case INPUT_REQUIRED -> updater.requiresInput(true);
        case COMPLETED -> updater.complete();
        case ERROR -> updater.fail();
        default -> throw new RuntimeException("Unknown status.");
      }
    }

    private String extractTextFromMessage(final Message message) {
      final StringBuilder builder = new StringBuilder();
      if (message.getParts() != null) {
        for (final Part<?> part : message.getParts()) {
          if (part instanceof TextPart textPart) {
            builder.append(textPart.getText());
          }
        }
      }
      return builder.toString();
    }

    @Override
    public void cancel(final RequestContext context,
                       final EventQueue eventQueue) throws JSONRPCError {
      var task = context.getTask();

      if (task.getStatus().state() == TaskState.CANCELED
        || task.getStatus().state() == TaskState.COMPLETED) {
        // task already canceled or completed
        throw new TaskNotCancelableError();
      }

      var updater = new TaskUpdater(context, eventQueue);
      updater.cancel();
    }
  }
}
