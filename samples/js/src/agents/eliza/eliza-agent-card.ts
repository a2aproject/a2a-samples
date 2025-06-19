import { AgentCard } from "@a2a-js/sdk";

export const elizaAgentCard = ( url?: string ): AgentCard => ({
    name: 'Eliza Agent',
    description: 'The classic AI chatbot from 1966',
    // Adjust the base URL and port as needed. /a2a is the default base in A2AExpressApp
    url, 
    provider: {
      organization: 'A2A Samples',
      url: 'https://example.com/a2a-samples' // Added provider URL
    },
    version: '0.0.1', // Incremented version
    capabilities: {
      streaming: true, // The new framework supports streaming
      pushNotifications: false, // Assuming not implemented for this agent yet
      stateTransitionHistory: true, // Agent uses history
    },
    // authentication: null, // Property 'authentication' does not exist on type 'AgentCard'.
    securitySchemes: undefined, // Or define actual security schemes if any
    security: undefined,
    defaultInputModes: ['text'],
    defaultOutputModes: ['text', 'task-status'], // task-status is a common output mode
    skills: [
      {
        id: 'therapy',
        name: 'Rogerian Psychotherapy',
        description: 'Provides Rogerian psychotherapy',
        tags: ['health', 'wellness', 'therapy'],
        examples: [
          'I feel like I am not good enough',
          'I am not sure what to do',
          'I am feeling overwhelmed',
          'I am not sure what to do'
        ],
        inputModes: ['text'], // Explicitly defining for skill
        outputModes: ['text', 'task-status'] // Explicitly defining for skill
      },
    ],
    supportsAuthenticatedExtendedCard: false,
  });