package io.a2a.extension.timestamp;

import io.a2a.server.agentexecution.AgentExecutor;
import io.a2a.server.agentexecution.RequestContext;
import io.a2a.server.events.EventQueue;
import io.a2a.spec.JSONRPCError;
import java.util.logging.Logger;

public class TimeStampAgentExecutorWrapper implements AgentExecutor {

    public static final String CORE_PATH = "github.com/a2aproject/a2a-samples/extensions/timestamp/v1";
    public static final String URI = "https://" + CORE_PATH;
    public static final String TIMESTAMP_FIELD = CORE_PATH + "/timestamp";

    private static final Logger logger = Logger.getLogger(TimeStampAgentExecutorWrapper.class.getName());
    private final AgentExecutor delegate;

    public TimeStampAgentExecutorWrapper(AgentExecutor delegate) {
        this.delegate = delegate;
    }

    @Override
    public void execute(RequestContext context, EventQueue eventQueue) throws JSONRPCError {
        if(isActivated(context)) {
            delegate.execute(context, new TimeStampEventQueue(eventQueue));
        } else {
            delegate.execute(context, eventQueue);
        }
    }

    @Override
    public void cancel(RequestContext context, EventQueue eventQueue) throws JSONRPCError {
        if(isActivated(context)) {
            delegate.cancel(context, new TimeStampEventQueue(eventQueue));
        } else {
            delegate.cancel(context, eventQueue);
        }
    }

    private boolean isActivated(final RequestContext context) {
        if (context.getCallContext().isExtensionActivated(URI)) {
            return true;
        }
        if (context.getCallContext().isExtensionRequested(URI)) {
            logger.info("Activated extension: " + URI);
            context.getCallContext().activateExtension(URI);
            return true;
        }
        return false;
    }
}
