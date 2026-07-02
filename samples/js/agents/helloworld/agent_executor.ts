import { v4 as uuidv4 } from 'uuid';

import {
  Artifact,
  Role,
  Task,
  TaskArtifactUpdateEvent,
  TaskState,
  TaskStatusUpdateEvent,
} from '@a2a-js/sdk';
import {
  AgentEvent,
  AgentExecutor,
  ExecutionEventBus,
  RequestContext,
  UnsupportedOperationError,
} from '@a2a-js/sdk/server';

// --8<-- [start:HelloWorldAgent]
export class HelloWorldAgent {
  /** Hello World Agent. */

  async invoke(userRequest: string): Promise<string> {
    /** Invoke the Hello World agent to generate a response. */
    return `Hello, World! I have received your request (${userRequest})`;
  }
}
// --8<-- [end:HelloWorldAgent]

// --8<-- [start:HelloWorldAgentExecutor_init]
export class HelloWorldAgentExecutor implements AgentExecutor {
  /** Test AgentProxy Implementation. */

  private readonly agent: HelloWorldAgent;

  constructor() {
    this.agent = new HelloWorldAgent();
  }
  // --8<-- [end:HelloWorldAgentExecutor_init]

  // --8<-- [start:HelloWorldAgentExecutor_execute]
  async execute(
    requestContext: RequestContext,
    eventBus: ExecutionEventBus
  ): Promise<void> {
    /** Process user request. */
    const userMessage = requestContext.userMessage;
    const existingTask = requestContext.task;
    const taskId = requestContext.taskId;
    const contextId = requestContext.contextId;

    // 1. Collect a task from request context or create snapshot
    const taskSnapshot: Task = existingTask ?? {
      id: taskId,
      contextId: contextId,
      status: {
        state: TaskState.TASK_STATE_SUBMITTED,
        timestamp: new Date().toISOString(),
        message: undefined,
      },
      artifacts: [],
      history: [userMessage],
      metadata: userMessage.metadata,
    };
    eventBus.publish(AgentEvent.task(taskSnapshot));

    // 2. Update task status to working
    const workingStatusUpdate: TaskStatusUpdateEvent = {
      taskId: taskId,
      contextId: contextId,
      status: {
        state: TaskState.TASK_STATE_WORKING,
        message: {
          role: Role.ROLE_AGENT,
          messageId: uuidv4(),
          parts: [
            {
              content: { $case: 'text', value: 'Processing request...' },
              metadata: undefined,
              filename: '',
              mediaType: 'text/plain',
            },
          ],
          taskId: taskId,
          contextId: contextId,
          extensions: [],
          metadata: {},
          referenceTaskIds: [],
        },
        timestamp: new Date().toISOString(),
      },
      metadata: {},
    };
    eventBus.publish(AgentEvent.statusUpdate(workingStatusUpdate));

    // 3. Collect user request from request content and invoke LLM agent
    const textPart = userMessage.parts.find(
      (p) => p.content?.$case === 'text'
    );
    const query =
      textPart?.content?.$case === 'text'
        ? textPart.content.value.trim()
        : '';

    let result: string;
    if (query) {
      result = await this.agent.invoke(query);
    } else {
      result = 'No text input is provided!';
    }

    // 4. Add generated response as an artifact
    const artifactId = uuidv4();
    const resultArtifact: Artifact = {
      artifactId: artifactId,
      name: 'Result',
      description: 'The response from the Hello World agent.',
      parts: [
        {
          content: { $case: 'text', value: result },
          metadata: undefined,
          filename: '',
          mediaType: 'text/plain',
        },
      ],
      metadata: undefined,
      extensions: [],
    };

    const artifactUpdate: TaskArtifactUpdateEvent = {
      taskId: taskId,
      contextId: contextId,
      artifact: resultArtifact,
      lastChunk: true,
      append: false,
      metadata: undefined,
    };
    eventBus.publish(AgentEvent.artifactUpdate(artifactUpdate));
    console.log('Result: ', result);

    // 5. Update task status to completed
    const finalUpdate: TaskStatusUpdateEvent = {
      taskId: taskId,
      contextId: contextId,
      status: {
        state: TaskState.TASK_STATE_COMPLETED,
        message: {
          role: Role.ROLE_AGENT,
          messageId: uuidv4(),
          parts: [
            {
              content: { $case: 'text', value: 'Request is completed!' },
              metadata: undefined,
              filename: '',
              mediaType: 'text/plain',
            },
          ],
          taskId: taskId,
          contextId: contextId,
          extensions: [],
          metadata: {},
          referenceTaskIds: [],
        },
        timestamp: new Date().toISOString(),
      },
      metadata: undefined,
    };
    eventBus.publish(AgentEvent.statusUpdate(finalUpdate));
  }
  // --8<-- [end:HelloWorldAgentExecutor_execute]

  // --8<-- [start:HelloWorldAgentExecutor_cancel]
  public cancelTask = async (
    _taskId: string,
    _eventBus: ExecutionEventBus
  ): Promise<void> => {
    /** Raise exception as cancel is not supported. */
    throw new UnsupportedOperationError('Cancel is not supported.');
  };
  // --8<-- [end:HelloWorldAgentExecutor_cancel]
}
