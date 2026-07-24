import express from 'express';
import {
  AgentCard,
} from '@a2a-js/sdk';
import {
  DefaultExecutionEventBusManager,
  DefaultRequestHandler,
  InMemoryTaskStore,
} from '@a2a-js/sdk/server';
import {
  agentCardHandler,
  jsonRpcHandler,
  UserBuilder,
} from '@a2a-js/sdk/server/express';

import { TimestampExtension } from './timestamp_ext/core.js';
import { wrapExecutor } from './timestamp_ext/server.js';
import { EchoExecutor } from './agent_executor.js';

const AGENT_URL = 'http://127.0.0.1:9998';

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
