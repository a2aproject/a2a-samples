import { IExecutionEventBus } from "../events/execution_event_bus.js";
import { RequestContext } from "./request_context.js";

export interface AgentExecutor {
    /**
     * Executes the agent logic based on the request context and publishes events.
     * @param requestContext The context of the current request.
     * @param eventBus The bus to publish execution events to.
     */
    execute: (
        requestContext: RequestContext,
        eventBus: IExecutionEventBus
    ) => Promise<void>;
}
