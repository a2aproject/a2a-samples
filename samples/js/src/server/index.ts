/**
 * Main entry point for the A2A Server V2 library.
 * Exports the server class, store implementations, and core types.
 */

// Export store-related types and implementations
export type { TaskStore } from "./store.js";
export { InMemoryTaskStore } from "./store.js";

// Export the custom error class
export { A2AError } from "./error.js";

export { A2AExpressApp } from "./a2a_express_app.js";
export type { AgentExecutor } from "./agent_execution/agent_executor.js";
export { RequestContext } from "./agent_execution/request_context.js";
export type { IExecutionEventBus } from "./events/execution_event_bus.js";
export { DefaultRequestHandler } from "./request_handler/default_request_handler.js";

// Re-export all schema types for convenience
export * as schema from "../schema.js";
