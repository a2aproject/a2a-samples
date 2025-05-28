# A2A Server (JS)

This directory contains a TypeScript server implementation for the Agent-to-Agent (A2A) communication protocol, built using Express.js.

## Basic Usage (Conceptual)

```typescript
import {
  InMemoryTaskStore,
  TaskStore,
  A2AExpressApp,
  AgentExecutor,
  RequestContext,
  IExecutionEventBus,
  DefaultRequestHandler,
} from "./index"; // Assuming imports from the server package

// 1. Define your agent's logic as a TaskHandler
class MyAgentExecutor implements AgentExecutor {
  async execute(
    requestContext: RequestContext,
    eventBus: IExecutionEventBus
  ): Promise<void> {
    const userMessage = requestContext.userMessage;
    const existingTask = requestContext.task;

    const taskId = existingTask?.id || uuidv4();
    const contextId = userMessage.contextId || existingTask?.contextId || uuidv4();

    console.log(
      `[MyAgentExecutor] Processing message ${userMessage.messageId} for task ${taskId} (context: ${contextId})`
    );

    // 1. Publish initial Task event if it's a new task
    if (!existingTask) {
      const initialTask: schema.Task = {
        kind: 'task',
        id: taskId,
        contextId: contextId,
        status: {
          state: schema.TaskState.Submitted,
          timestamp: new Date().toISOString(),
        },
        history: [userMessage],
        metadata: userMessage.metadata,
        artifacts: [], // Initialize artifacts array
      };
      eventBus.publish(initialTask);
    }

    // 2. Publish "working" status update
    const workingStatusUpdate: schema.TaskStatusUpdateEvent = {
      kind: 'status-update',
      taskId: taskId,
      contextId: contextId,
      status: {
        state: schema.TaskState.Working,
        message: {
          kind: 'message',
          role: 'agent',
          messageId: uuidv4(),
          parts: [{ kind: 'text', text: 'Generating code...' }],
          taskId: taskId,
          contextId: contextId,
        },
        timestamp: new Date().toISOString(),
      },
      final: false,
    };
    eventBus.publish(workingStatusUpdate);

    // Simulate work...
    await new Promise((resolve) => setTimeout(resolve, 1000));

    // Check for request cancellation
    if (requestContext.isCancelled()) {
      console.log(`[MyAgentExecutor] Request cancelled for task: ${taskId}`);
      const cancelledUpdate: schema.TaskStatusUpdateEvent = {
        kind: 'status-update',
        taskId: taskId,
        contextId: contextId,
        status: {
          state: schema.TaskState.Canceled,
          timestamp: new Date().toISOString(),
        },
        final: true,
      };
      eventBus.publish(cancelledUpdate);
      return;
    }

    // 3. Publish artifact update
    const artifactUpdate: schema.TaskArtifactUpdateEvent = {
      kind: 'artifact-update',
      taskId: taskId,
      contextId: contextId,
      artifact: {
        artifactId: "artifact-1",
        name: "artifact-1",
        parts: [{ text: `Task ${context.task.id} completed.` }],
      },
      append: false, // Each emission is a complete file snapshot
      lastChunk: true, // True for this file artifact
    };
    eventBus.publish(artifactUpdate);

    // 4. Publish final status update
    const finalUpdate: schema.TaskStatusUpdateEvent = {
      kind: 'status-update',
      taskId: taskId,
      contextId: contextId,
      status: {
        state: schema.TaskState.Completed,
        message: {
          kind: 'message',
          role: 'agent',
          messageId: uuidv4(),
          taskId: taskId,
          contextId: contextId,
        },
        timestamp: new Date().toISOString(),
      },
      final: true,
    };
    eventBus.publish(finalUpdate);
  }
}

// 2. Create and start the server
const taskStore: TaskStore = new InMemoryTaskStore();
const agentExecutor: AgentExecutor = new MyAgentExecutor();

const requestHandler = new DefaultRequestHandler(
  coderAgentCard,
  taskStore,
  agentExecutor
);

const appBuilder = new A2AExpressApp(requestHandler);
const expressApp = appBuilder.setupRoutes(express(), '');

const PORT = process.env.CODER_AGENT_PORT || 41242; // Different port for coder agent
expressApp.listen(PORT, () => {
  console.log(`[MyAgent] Server using new framework started on http://localhost:${PORT}`);
  console.log(`[MyAgent] Agent Card: http://localhost:${PORT}/.well-known/agent.json`);
  console.log('[MyAgent] Press Ctrl+C to stop the server');
});
```

This server implementation provides a foundation for building A2A-compliant agents in TypeScript.
