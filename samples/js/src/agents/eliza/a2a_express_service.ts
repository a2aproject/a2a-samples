/**
 * A2AExpressService provides endpoints for an A2A service agent card and JSON-RPC requests.
 * This class supports multiple A2A services on the same server, as well as support for
 * universal authentication and agent multi-tenancy.
 * 
 * Agent multi-tenancy is the ability of one agent to represent multiple users.  For example, an
 * (Eliza) therapist agent POST /message to the "Joseph" therapist would reply as Joseph, whereas the
 * same agent POST /message to the "Sarah" therapist would reply as Sarah.
 * 
 * To see multi-tenancy in production, see [Matchwise](https://matchwise.ai) where the Connect agent represents
 * many users to provide personalized business networking advice.
 * 
 * Universal authentication is the ability to authenticate any client without the need for 
 * an authentication service like OAuth.  Universal authentication uses public key cryptography
 * where the public keys for clients are distributed in W3C DID documents.
 */

import { Request, Response, Router } from 'express';
import { Resolver } from "did-resolver";
import {
    b64u,
    ClientAgentSession,
    ClientAgentSessionStore,
    createChallenge,
    handleAuthorization,
} from "@agentic-profile/auth";
import {
    A2AResponse,
    JSONRPCErrorResponse,
    JSONRPCSuccessResponse,
} from "@a2a-js/sdk"; // Import common types
import {
    A2AError,
    A2ARequestHandler,
    JsonRpcTransportHandler,
} from "@a2a-js/sdk/server"; // Import server components

export type AgentSessionResolver = (req: Request, res: Response) => Promise<ClientAgentSession | null>

/**
 * Options for configuring the A2AService.
 */
export interface A2AServiceOptions {
    /** Task storage implementation. Defaults to InMemoryTaskStore. */
    //taskStore?: TaskStore;

    /** URL Path for the A2A endpoint. If not provided, the req.originalUrl is used. */
    agentPath?: string;

    /** Agent session resolver. If not defined, then universal authentication is not supported. */
    agentSessionResolver?: AgentSessionResolver
}

export class A2AExpressService {
    private requestHandler: A2ARequestHandler; // Kept for getAgentCard
    private jsonRpcTransportHandler: JsonRpcTransportHandler;
    private options: A2AServiceOptions;

    constructor(requestHandler: A2ARequestHandler, options?: A2AServiceOptions) {
        this.requestHandler = requestHandler; // DefaultRequestHandler instance
        this.jsonRpcTransportHandler = new JsonRpcTransportHandler(requestHandler);
        this.options = options;
    }

    public cardEndpoint = async (req: Request, res: Response) => {
        try {
            // resolve agent service endpoint
            let url: string;
            if (this.options?.agentPath) {
                url = `${req.protocol}://${req.get('host')}${this.options.agentPath}`;
            } else {
                /* If there's no explicit agent path, then derive one from the Express
                 Request originalUrl by removing the trailing /agent.json if present */
                const baseUrl = req.originalUrl.replace(/\/agent\.json$/, '');
                url = `${req.protocol}://${req.get('host')}${baseUrl}`;
            }

            const agentCard = await this.requestHandler.getAgentCard();
            res.json({ ...agentCard, url });
        } catch (error: unknown) {
            console.error("Error fetching agent card:", error);
            res.status(500).json({ error: "Failed to retrieve agent card" });
        }
    }

    public agentEndpoint = async (req: Request, res: Response) => {
        try {
            // Handle client authentication
            let agentSession: ClientAgentSession | null = null;
            if (this.options?.agentSessionResolver) {
                agentSession = await this.options.agentSessionResolver(req, res);
                if (!agentSession)
                    return; // 401 response with challenge already issued
                else console.log("Agent session resolved:", agentSession.id, agentSession.agentDid);
            }

            const rpcResponseOrStream = await this.jsonRpcTransportHandler.handle(req.body);

            // Check if it's an AsyncGenerator (stream)
            if (typeof (rpcResponseOrStream as unknown)?.[Symbol.asyncIterator] === 'function') {
                const stream = rpcResponseOrStream as AsyncGenerator<JSONRPCSuccessResponse, void, undefined>;

                res.setHeader('Content-Type', 'text/event-stream');
                res.setHeader('Cache-Control', 'no-cache');
                res.setHeader('Connection', 'keep-alive');
                res.flushHeaders();

                try {
                    for await (const event of stream) {
                        // Each event from the stream is already a JSONRPCResult
                        res.write(`id: ${new Date().getTime()}\n`);
                        res.write(`data: ${JSON.stringify(event)}\n\n`);
                    }
                } catch (streamError: unknown) {
                    console.error(`Error during SSE streaming (request ${req.body?.id}):`, streamError);
                    // If the stream itself throws an error, send a final JSONRPCErrorResponse
                    const a2aError = streamError instanceof A2AError ? streamError : A2AError.internalError((streamError as Error).message || 'Streaming error.');
                    const errorResponse: JSONRPCErrorResponse = {
                        jsonrpc: '2.0',
                        id: req.body?.id || null, // Use original request ID if available
                        error: a2aError.toJSONRPCError(),
                    };
                    if (!res.headersSent) { // Should not happen if flushHeaders worked
                        res.status(500).json(errorResponse); // Should be JSON, not SSE here
                    } else {
                        // Try to send as last SSE event if possible, though client might have disconnected
                        res.write(`id: ${new Date().getTime()}\n`);
                        res.write(`event: error\n`); // Custom event type for client-side handling
                        res.write(`data: ${JSON.stringify(errorResponse)}\n\n`);
                    }
                } finally {
                    if (!res.writableEnded) {
                        res.end();
                    }
                }
            } else { // Single JSON-RPC response
                const rpcResponse = rpcResponseOrStream as A2AResponse;
                res.status(200).json(rpcResponse);
            }
        } catch (error: unknown) { // Catch errors from jsonRpcTransportHandler.handle itself (e.g., initial parse error)
            console.error("Unhandled error in A2AExpressApp POST handler:", error);
            const a2aError = error instanceof A2AError ? error : A2AError.internalError('General processing error.');
            const errorResponse: JSONRPCErrorResponse = {
                jsonrpc: '2.0',
                id: req.body?.id || null,
                error: a2aError.toJSONRPCError(),
            };
            if (!res.headersSent) {
                res.status(500).json(errorResponse);
            } else if (!res.writableEnded) {
                // If headers sent (likely during a stream attempt that failed early), try to end gracefully
                res.end();
            }
        }
    }

    /**
     * Adds A2A routes to an existing Express app.
     * @param app Optional existing Express app.
     * @param baseUrl The base URL for A2A endpoints (e.g., "/a2a/api").
     * @returns The Express app with A2A routes.
     */
    public routes(): Router {
        const router = Router();

        router.get("/agent.json", this.cardEndpoint);

        router.post("/", this.agentEndpoint);

        // The separate /stream endpoint is no longer needed.
        return router;
    }
}

/**
  * If an authorization header is provided, then an attemot to resolve an agent session is made,
  * otherwise a 401 response with a new challenge in the WWW-Authenticate header.
  * @returns a ClientAgentSession, or null if request handled by 401/challenge
  * @throws {Error} if authorization header is invalid.  If authorization is expired or not
  *   found, then no error is thrown and instead a new challenge is issued.
  */
export async function resolveAgentSession(
    req: Request,
    res: Response,
    store: ClientAgentSessionStore,
    didResolver: Resolver
): Promise<ClientAgentSession | null> {
    const { authorization } = req.headers;
    if (authorization) {
        const agentSession = await handleAuthorization(authorization, store, didResolver);
        if (agentSession)
            return agentSession;
    }

    const challenge = await createChallenge(store);
    res.status(401)
        .set('WWW-Authenticate', `Agentic ${b64u.objectToBase64Url(challenge)}`)
        .end();
    return null;
}
