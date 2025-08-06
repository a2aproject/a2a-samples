import { createDidResolver } from "@agentic-profile/common";
import { Request, Response } from "express";
import {
    TaskStore,
} from "@a2a-js/sdk";
import {
    InMemoryTaskStore,
    AgentExecutor,
    DefaultRequestHandler,
} from "@a2a-js/sdk/server";

import { A2AExpressService, resolveAgentSession } from "./a2a_express_service.js";
import express from "express";
import { elizaAgentCard } from "./eliza-agent-card.js";
import { ElizaAgentExecutor } from "./eliza-agent.js";

import { InMemoryUnifiedStore } from "./store.js";
const unifiedStore = new InMemoryUnifiedStore();

async function main() {
    const PORT = process.env.PORT || 41241;

    // 1. Prepare TaskStore and AgentExecutor
    const taskStore: TaskStore = new InMemoryTaskStore();
    const agentExecutor: AgentExecutor = new ElizaAgentExecutor(unifiedStore);

    // 2. Create DefaultRequestHandler.  This can be used by both the well-known and authenticated agents.
    const agentCard = elizaAgentCard();
    const requestHandler = new DefaultRequestHandler(
        agentCard,
        taskStore,
        agentExecutor
    );

    // 3. Create and setup A2A app
    const app = express();
    app.use(express.json());

    // 4. Create a "well-known" Eliza with no authentication
    const openAgentPath = "/";
    const wellKnownService = new A2AExpressService(requestHandler, { agentPath: openAgentPath });
    app.use(openAgentPath, wellKnownService.routes());
    const wellKnownCardPath = "/.well-known/agent.json";
    app.get(wellKnownCardPath, wellKnownService.cardEndpoint);

    // 5. Prepare to resolve DIDs and agent sessions for universal authentication
    const didResolver = createDidResolver();
    const agentSessionResolver = async (req: Request, res: Response) => {
        return resolveAgentSession(req, res, unifiedStore, didResolver);
    }

    // 6. Create an Eliza at "/agents/eliza" that requires authentication
    const a2aServiceWithAuth = new A2AExpressService(requestHandler, { agentSessionResolver });
    const secureAgentPath = "/agents/eliza";
    app.use(secureAgentPath, a2aServiceWithAuth.routes());

    // 7. Start the server
    const baseUrl = `http://localhost:${PORT}`;
    app.listen(PORT, () => {
        console.log(`[ElizaAgent] Server using new framework started on ${baseUrl}`);
        console.log(`[ElizaAgent]   Open Agent Card: ${baseUrl}${wellKnownCardPath}`);
        console.log(`[ElizaAgent]   Open Agent Card: ${baseUrl}${openAgentPath}agent.json`);
        console.log(`[ElizaAgent] Secure Agent Card: ${baseUrl}${secureAgentPath}/agent.json`);
        console.log('[ElizaAgent] Press Ctrl+C to stop the server');
    });
}

main().catch(console.error);
