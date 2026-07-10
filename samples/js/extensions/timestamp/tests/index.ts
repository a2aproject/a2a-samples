import express from 'express';
import { v4 as uuidv4 } from 'uuid';
import {
  AgentCard,
  AgentSkill,
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
  DefaultExecutionEventBusManager,
  DefaultRequestHandler,
  ExecutionEventBus,
  InMemoryTaskStore,
  RequestContext,
  UnsupportedOperationError,
} from '@a2a-js/sdk/server';
import {
  agentCardHandler,
  jsonRpcHandler,
  UserBuilder,
} from '@a2a-js/sdk/server/express';

import { TimestampExtension } from '../timestamp_ext/core.js';
import { wrapExecutor } from '../timestamp_ext/server.js';

const AGENT_URL = 'http://127.0.0.1:9998';

class EchoExecutor implements AgentExecutor {
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

    const artifact: Artifact = {
      artifactId: uuidv4(),
      name: 'result',
      description: 'echo result',
      parts: [{ content: { $case: 'text', value: 'hello!' }, mediaType: 'text/plain', filename: '', metadata: {} }],
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

  public cancelTask = async (
    _taskId: string,
    _eventBus: ExecutionEventBus
  ): Promise<void> => {
    throw new UnsupportedOperationError('Cancel is not supported.');
  };
}

const fixedTs = process.env.TIMESTAMP_EXT_FIXED_CLOCK;
const ext = fixedTs
  ? new TimestampExtension(() => parseFloat(fixedTs))
  : new TimestampExtension();

const baseCard: AgentCard = {
  provider: undefined,
  name: 'Echo',
  description: 'echo agent that demonstrates the timestamp extension',
  version: '1.0.0',
  defaultInputModes: ['text'],
  defaultOutputModes: ['text'],
  capabilities: {
    streaming: true,
    extendedAgentCard: false,
    extensions: [],
    pushNotifications: false,
  },
  supportedInterfaces: [
    {
      protocolBinding: 'JSONRPC',
      protocolVersion: '1.0',
      url: AGENT_URL,
      tenant: '',
    },
  ],
  skills: [],
  securitySchemes: {},
  securityRequirements: [],
  signatures: [],
};

const card = ext.addToCard(baseCard);

const requestHandler = new DefaultRequestHandler(
  card,
  new InMemoryTaskStore(),
  wrapExecutor(new EchoExecutor(), ext),
  new DefaultExecutionEventBusManager()
);

const app = express();
app.use(express.json());

app.use(
  '/.well-known/agent-card.json',
  agentCardHandler({ agentCardProvider: async () => card })
);

app.use(
  '/',
  jsonRpcHandler({
    requestHandler,
    userBuilder: UserBuilder.noAuthentication,
  })
);

app.listen(9998, () => {
  console.log('[TimestampEchoServer] Server started on http://127.0.0.1:9998');
});
