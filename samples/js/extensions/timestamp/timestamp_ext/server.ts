/* eslint-disable n/no-missing-import */
import { AgentExecutor } from "@a2a-js/sdk/server";
import { TimestampExtension, URI } from "./core.js";

export function wrapExecutor(
    executor: AgentExecutor,
    ext: TimestampExtension
): AgentExecutor {
    return {
        execute: async (context, eventBus) => {
            if (ext.isRequested(context)) {
                // Activate the extension in the context so the response header is sent back
                context.context.addActivatedExtension(URI);

                // Monkeypatch the publish method to inject timestamps
                const originalPublish = eventBus.publish.bind(eventBus);
                eventBus.publish = (event) => {
                    ext.timestampEvent(event);
                    originalPublish(event);
                };
            }
            return executor.execute(context, eventBus);
        },
        cancelTask: async (taskId, eventBus) => {
            return executor.cancelTask(taskId, eventBus);
        },
    };
}
