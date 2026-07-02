import express from 'express';

import {
  A2A_PROTOCOL_VERSION,
  AGENT_CARD_PATH,
  AgentCard,
  AgentSkill,
} from '@a2a-js/sdk';
import {
  DefaultRequestHandler,
  InMemoryTaskStore,
} from '@a2a-js/sdk/server';
import {
  agentCardHandler,
  jsonRpcHandler,
  UserBuilder,
} from '@a2a-js/sdk/server/express';

import { HelloWorldAgentExecutor } from './agent_executor.js';

// --8<-- [start:AgentSkill]
// Defines the abilities or functions that agent can perform.
const skill: AgentSkill = {
  id: 'echo_bot',
  name: 'Echo Bot',
  description:
    'An example agent that acknowledges client request and responds with a "Hello World" message.',
  inputModes: ['text/plain'],
  outputModes: ['text/plain'],
  tags: ['a2a', 'echo-example'],
  examples: ['hi', 'how are you'],
  securityRequirements: [],
};
// --8<-- [end:AgentSkill]

// Defines an optional additional skill for the agent that is not visible in the public card.
const extendedSkill: AgentSkill = {
  id: 'echo_bot_super_mode',
  name: 'Echo Bot (Super Mode)',
  description:
    'An extended version of Echo Bot that responds with extra enthusiasm!',
  inputModes: ['text/plain'],
  outputModes: ['text/plain'],
  tags: ['a2a', 'echo-example', 'extended'],
  examples: ['super hi', 'give me a super hello'],
  securityRequirements: [],
};

// --8<-- [start:AgentCard]
// Define a public-facing agent card that allows clients to discover your agent's capabilities.
const publicAgentCard: AgentCard = {
  // Basic identity information of A2A server
  name: 'Hello World Agent',
  description: 'Just a hello world agent',
  version: '0.0.1',
  // Default Media Types for the agent's interactions
  defaultInputModes: ['text/plain'],
  defaultOutputModes: ['text/plain'],
  // Supported A2A features
  capabilities: {
    streaming: true,
    pushNotifications: false,
    extensions: [],
    extendedAgentCard: true,
  },
  // Supported interfaces and endpoints
  supportedInterfaces: [
    {
      url: 'http://127.0.0.1:9999/',
      protocolBinding: 'JSONRPC',
      tenant: '',
      protocolVersion: A2A_PROTOCOL_VERSION,
    },
  ],
  provider: {
    organization: 'A2A Samples',
    url: 'https://example.com/a2a-samples',
  },
  // The list of AgentSkill objects that this agent offers
  skills: [skill],
  securitySchemes: {},
  securityRequirements: [],
  documentationUrl: '',
  signatures: [],
};
// --8<-- [end:AgentCard]

// Defines the authenticated extended agent card with
// extended skills that are visible only to authenticated users
const extendedAgentCard: AgentCard = {
  name: 'Hello World Agent - Extended Edition',
  description:
    'The full-featured hello world agent for authenticated users.',
  version: '0.0.2',
  defaultInputModes: ['text/plain'],
  defaultOutputModes: ['text/plain'],
  capabilities: {
    streaming: true,
    pushNotifications: false,
    extensions: [],
    extendedAgentCard: true,
  },
  supportedInterfaces: [
    {
      url: 'http://127.0.0.1:9999/',
      protocolBinding: 'JSONRPC',
      tenant: '',
      protocolVersion: A2A_PROTOCOL_VERSION,
    },
  ],
  provider: {
    organization: 'A2A Samples',
    url: 'https://example.com/a2a-samples',
  },
  skills: [skill, extendedSkill],
  securitySchemes: {},
  securityRequirements: [],
  documentationUrl: '',
  signatures: [],
};

async function main() {
  // --8<-- [start:RequestHandler]
  // The RequestHandler processes incoming requests and manages tasks
  const taskStore = new InMemoryTaskStore();
  const agentExecutor = new HelloWorldAgentExecutor();

  const requestHandler = new DefaultRequestHandler(
    publicAgentCard,
    taskStore,
    agentExecutor,
    undefined, // eventBusManager
    undefined, // pushNotificationManager
    undefined, // pushNotificationSender
    extendedAgentCard
  );
  // --8<-- [end:RequestHandler]

  // --8<-- [start:ServerRoutes]
  const app = express();

  // Create routes for the agent card
  app.use(
    `/${AGENT_CARD_PATH}`,
    agentCardHandler({ agentCardProvider: requestHandler })
  );

  // Create routes for JSON-RPC
  app.use(
    '/',
    jsonRpcHandler({
      requestHandler,
      userBuilder: UserBuilder.noAuthentication,
    })
  );
  // --8<-- [end:ServerRoutes]

  // --8<-- [start:AppServer]
  const PORT = process.env.PORT || 9999;
  app.listen(PORT, () => {
    console.log(
      `[HelloWorldAgent] Server started on http://127.0.0.1:${PORT}`
    );
    console.log(
      `[HelloWorldAgent] Agent Card: http://127.0.0.1:${PORT}/.well-known/agent-card.json`
    );
  });
  // --8<-- [end:AppServer]
}

main().catch(console.error);
