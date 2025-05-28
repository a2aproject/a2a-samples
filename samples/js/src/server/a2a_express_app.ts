import express, { Request, Response, Express } from 'express';

import { A2AError } from "./error.js";
import { schema } from "./index.js";
import { A2ARequestHandler } from "./request_handler/a2a_request_handler.js";
import { JsonRpcTransportHandler } from "./transports/jsonrpc_transport_handler.js";

export class A2AExpressApp {
    private requestHandler: A2ARequestHandler; // Kept for getAgentCard
    private jsonRpcTransportHandler: JsonRpcTransportHandler;

    constructor(requestHandler: A2ARequestHandler) {
        this.requestHandler = requestHandler; // DefaultRequestHandler instance
        this.jsonRpcTransportHandler = new JsonRpcTransportHandler(requestHandler);
    }

    /**
     * Adds A2A routes to an existing Express app.
     * @param app Optional existing Express app.
     * @param baseUrl The base URL for A2A endpoints (e.g., "/a2a/api").
     * @returns The Express app with A2A routes.
     */
    public setupRoutes(app: Express, baseUrl: string = ''): Express {
        app.use(express.json());

        app.get(`${baseUrl}/.well-known/agent.json`, async (req: Request, res: Response) => {
            try {
                // getAgentCard is on A2ARequestHandler, which DefaultRequestHandler implements
                const agentCard = await this.requestHandler.getAgentCard();
                res.json(agentCard);
            } catch (error: any) {
                console.error("Error fetching agent card:", error);
                res.status(500).json({ error: "Failed to retrieve agent card" });
            }
        });

        app.post(baseUrl, async (req: Request, res: Response) => {
            try {
                const rpcResponseOrStream = await this.jsonRpcTransportHandler.handle(req.body);

                // Check if it's an AsyncGenerator (stream)
                if (typeof (rpcResponseOrStream as any)?.[Symbol.asyncIterator] === 'function') {
                    const stream = rpcResponseOrStream as AsyncGenerator<schema.JSONRPCResult, void, undefined>;

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
                    } catch (streamError: any) {
                        console.error(`Error during SSE streaming (request ${req.body?.id}):`, streamError);
                        // If the stream itself throws an error, send a final JSONRPCErrorResponse
                        const a2aError = streamError instanceof A2AError ? streamError : A2AError.internalError(streamError.message || 'Streaming error.');
                        const errorResponse: schema.JSONRPCErrorResponse = {
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
                    const rpcResponse = rpcResponseOrStream as schema.A2AResponse;
                    res.status(200).json(rpcResponse);
                }
            } catch (error: any) { // Catch errors from jsonRpcTransportHandler.handle itself (e.g., initial parse error)
                console.error("Unhandled error in A2AExpressApp POST handler:", error);
                const a2aError = error instanceof A2AError ? error : A2AError.internalError('General processing error.');
                const errorResponse: schema.JSONRPCErrorResponse = {
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
        });
        // The separate /stream endpoint is no longer needed.
        return app;
    }
}
