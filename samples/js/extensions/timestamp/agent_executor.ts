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
  AgentExecutor,
  ExecutionEventBus,
  AgentEvent,
  RequestContext,
  UnsupportedOperationError,
} from '@a2a-js/sdk/server';

class EchoAgent {
  async invoke(userRequest: string): Promise<string> {
    if (userRequest) {
      return `hello! (${userRequest})`;
    }
    return 'hello!';
  }
}

export class EchoExecutor implements AgentExecutor {
  private agent = new EchoAgent();

  async execute(
    requestContext: RequestContext,
    eventBus: ExecutionEventBus
  ): Promise<void> {
    const userMessage = requestContext.userMessage;
    const existingTask = requestContext.task;
    const taskId = requestContext.taskId;
    const contextId = requestContext.contextId;

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

    const workingStatus: TaskStatusUpdateEvent = {
      taskId: taskId,
      contextId: contextId,
      status: {
        state: TaskState.TASK_STATE_WORKING,
        message: {
          role: Role.ROLE_AGENT,
          messageId: uuidv4(),
          parts: [{ content: { $case: 'text', value: 'working...' }, mediaType: 'text/plain', filename: '', metadata: {} }],
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
    eventBus.publish(AgentEvent.statusUpdate(workingStatus));

    let query = '';
    if (userMessage.parts) {
      for (const part of userMessage.parts) {
        if (part.content?.$case === 'text') {
          query = part.content.value;
          break;
        }
      }
    }

    const result = await this.agent.invoke(query);

    const artifact: Artifact = {
      artifactId: uuidv4(),
      name: 'result',
      description: 'echo result',
      parts: [{ content: { $case: 'text', value: result }, mediaType: 'text/plain', filename: '', metadata: {} }],
      extensions: [],
      metadata: {},
    };

    const artifactUpdate: TaskArtifactUpdateEvent = {
      taskId: taskId,
      contextId: contextId,
      artifact: artifact,
      lastChunk: true,
      append: false,
      metadata: {},
    };
    eventBus.publish(AgentEvent.artifactUpdate(artifactUpdate));

    const completedStatus: TaskStatusUpdateEvent = {
      taskId: taskId,
      contextId: contextId,
      status: {
        state: TaskState.TASK_STATE_COMPLETED,
        timestamp: new Date().toISOString(),
        message: undefined,
      },
      metadata: {},
    };
    eventBus.publish(AgentEvent.statusUpdate(completedStatus));
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  public cancelTask = async (
    _taskId: string,
    _eventBus: ExecutionEventBus
  ): Promise<void> => {
    throw new UnsupportedOperationError('Cancel is not supported.');
  };
}
