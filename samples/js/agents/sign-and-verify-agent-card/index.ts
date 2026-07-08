import express from 'express';
import * as crypto from 'node:crypto';
import * as fs from 'node:fs';
import * as path from 'node:path';

import {
  AgentCard,
  AgentSkill,
  generateAgentCardSignature,
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

import { SignedAgentExecutor } from './agent_executor.js';

function createPublicPrivateKeys(): { privateKey: crypto.KeyObject; publicKeyPem: string } {
  /** Generate EC private and public key pair as PEM-encoded strings. */
  const { privateKey, publicKey } = crypto.generateKeyPairSync('ec', {
    namedCurve: 'P-256',
  });
  const publicKeyPem = publicKey.export({ type: 'spki', format: 'pem' }).toString('utf-8');
  return { privateKey, publicKeyPem };
}

// Generate a private, public key pair
const { privateKey, publicKeyPem } = createPublicPrivateKeys();

// Save public key to a file
const keyId = 'my-key';
const keys = { [keyId]: publicKeyPem };
fs.writeFileSync('public_keys.json', JSON.stringify(keys, null, 2));

const skill: AgentSkill = {
  id: 'reminder',
  name: 'Verification Reminder',
  description: 'Reminds the user to verify the Agent Card.',
  tags: ['verify me'],
  examples: ['Verify me!'],
  inputModes: ['text'],
  outputModes: ['text'],
  securityRequirements: [],
};

const extendedSkill: AgentSkill = {
  id: 'reminder-please',
  name: 'Verification Reminder Please!',
  description: 'Politely reminds user to verify the Agent Card.',
  tags: ['verify me', 'pretty please', 'extended'],
  examples: ['Verify me, pretty please! :)', 'Please verify me.'],
  inputModes: ['text'],
  outputModes: ['text'],
  securityRequirements: [],
};

const publicAgentCard: AgentCard = {
  name: 'Signed Agent',
  description: 'Public card containing basic skills of the signed agent.',
  iconUrl: 'http://localhost:9999/',
  version: '1.0.0',
  defaultInputModes: ['text'],
  defaultOutputModes: ['text'],
  capabilities: {
    streaming: true,
    extendedAgentCard: true,
    extensions: [],
    pushNotifications: false,
  },
  supportedInterfaces: [
    {
      protocolBinding: 'JSONRPC',
      protocolVersion: '1.0',
      url: 'http://localhost:9999',
      tenant: '',
    },
  ],
  skills: [skill],
  provider: undefined,
  securitySchemes: {},
  securityRequirements: [],
  signatures: [],
};

const extendedAgentCard: AgentCard = {
  name: 'Signed Agent - Extended Card',
  description: 'Extended card containing additional capabilities of the signed agent.',
  iconUrl: 'http://localhost:9999/',
  version: '1.0.1',
  defaultInputModes: ['text'],
  defaultOutputModes: ['text'],
  capabilities: {
    streaming: true,
    extendedAgentCard: true,
    extensions: [],
    pushNotifications: false,
  },
  supportedInterfaces: [
    {
      protocolBinding: 'JSONRPC',
      protocolVersion: '1.0',
      url: 'http://localhost:9999',
      tenant: '',
    },
  ],
  skills: [skill, extendedSkill],
  provider: undefined,
  securitySchemes: {},
  securityRequirements: [],
  signatures: [],
};

// Create signer function which will be used for AgentCard signing
const signer = generateAgentCardSignature(
  privateKey,
  {
    kid: keyId,
    alg: 'ES256',
    jku: 'http://localhost:9999/public_keys.json',
    typ: 'JWT',
  }
);

const signedPublicCard = await signer(publicAgentCard);

const requestHandler = new DefaultRequestHandler(
  signedPublicCard,
  new InMemoryTaskStore(),
  new SignedAgentExecutor(),
  new DefaultExecutionEventBusManager(),
  undefined,
  undefined,
  // Serves the extended agent card signed dynamically using signer for authorized client queries
  async () => extendedAgentCard,
  signer
);

const app = express();
app.use(express.json());

app.use(
  '/.well-known/agent-card.json',
  agentCardHandler({ agentCardProvider: async () => signedPublicCard })
);

app.use(
  '/',
  jsonRpcHandler({
    requestHandler,
    userBuilder: UserBuilder.noAuthentication,
  })
);

// Expose the public key for verification purposes
// Contents of public_keys.json will be fetched on the client side during AgentCard signatures verification
app.get('/public_keys.json', (_req, res) => {
  res.sendFile(path.resolve('public_keys.json'));
});

app.listen(9999, () => {
  console.log('Starting server on http://127.0.0.1:9999...');
});
