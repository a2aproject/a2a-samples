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

// --8<-- [start:SignedAgentExecutor]
export class SignedAgentExecutor implements AgentExecutor {
  /** Test AgentProxy Implementation. */

  async execute(
    requestContext: RequestContext,
    eventBus: ExecutionEventBus
  ): Promise<void> {
    /** Execute the agent and manage task lifecycle events. */
    const userMessage = requestContext.userMessage;
    const existingTask = requestContext.task;
    const taskId = requestContext.taskId;
    const contextId = requestContext.contextId;

    // 1. Collect a task from request context
    if (!existingTask) {
      const initialTask: Task = {
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
      eventBus.publish(AgentEvent.task(initialTask));
    }

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
              content: { $case: 'text', value: 'Processing verification request...' },
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

    // 3. Collect user request from request content and generate content
    const textPart = userMessage.parts.find(
      (p) => p.content?.$case === 'text'
    );
    const query =
      textPart?.content?.$case === 'text'
        ? textPart.content.value.trim()
        : '';

    const result = query ? `Verify me! (${query})` : 'Verify me!';

    // 4. Add generated response as an artifact
    const artifactId = uuidv4();
    const resultArtifact: Artifact = {
      artifactId: artifactId,
      name: 'Result',
      description: 'Verification result artifact.',
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

  public cancelTask = async (
    _taskId: string,
    _eventBus: ExecutionEventBus
  ): Promise<void> => {
    /** Raise exception as cancel is not supported. */
    throw new UnsupportedOperationError('Cancel is not supported.');
  };
}
// --8<-- [end:SignedAgentExecutor]
