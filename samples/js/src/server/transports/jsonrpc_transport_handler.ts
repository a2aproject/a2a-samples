import { JSONRPCMessage, JSONRPCRequest, JSONRPCErrorResponse, MessageSendParams, TaskQueryParams, TaskIdParams, TaskPushNotificationConfig, JSONRPCResult, A2AResponse } from "../../schema.js";
import { A2AError } from "../error.js";
import { A2ARequestHandler } from "../request_handler/a2a_request_handler.js";

/**
 * Handles JSON-RPC transport layer, routing requests to A2ARequestHandler.
 */
export class JsonRpcTransportHandler {
    private requestHandler: A2ARequestHandler;

    constructor(requestHandler: A2ARequestHandler) {
        this.requestHandler = requestHandler;
    }

    /**
     * Handles an incoming JSON-RPC request.
     * For streaming methods, it returns an AsyncGenerator of JSONRPCResult.
     * For non-streaming methods, it returns a Promise of a single JSONRPCMessage (Result or ErrorResponse).
     */
    public async handle(
        requestBody: any
    ): Promise<A2AResponse | AsyncGenerator<A2AResponse, void, undefined>> {
        let rpcRequest: JSONRPCRequest;

        try {
            if (typeof requestBody === 'string') {
                rpcRequest = JSON.parse(requestBody);
            } else if (typeof requestBody === 'object' && requestBody !== null) {
                rpcRequest = requestBody as JSONRPCRequest;
            } else {
                throw A2AError.parseError('Invalid request body type.');
            }

            if (
                rpcRequest.jsonrpc !== '2.0' ||
                !rpcRequest.method ||
                typeof rpcRequest.method !== 'string'
            ) {
                throw A2AError.invalidRequest(
                    'Invalid JSON-RPC request structure.'
                );
            }
        } catch (error: any) {
            const a2aError = error instanceof A2AError ? error : A2AError.parseError(error.message || 'Failed to parse JSON request.');
            return {
                jsonrpc: '2.0',
                id: (typeof rpcRequest!?.id !== 'undefined' ? rpcRequest!.id : null),
                error: a2aError.toJSONRPCError(),
            } as JSONRPCErrorResponse;
        }

        const { method, params = {}, id: requestId = null } = rpcRequest;

        try {
            if (method === 'message/stream' || method === 'tasks/resubscribe') {
                const agentCard = await this.requestHandler.getAgentCard();
                if (!agentCard.capabilities.streaming) {
                    throw A2AError.unsupportedOperation(`Method ${method} requires streaming capability.`);
                }
                const agentEventStream = method === 'message/stream'
                    ? this.requestHandler.sendMessageStream(params as MessageSendParams)
                    : this.requestHandler.resubscribe(params as TaskIdParams);

                // Wrap the agent event stream into a JSON-RPC result stream
                return (async function* jsonRpcEventStream(): AsyncGenerator<JSONRPCResult, void, undefined> {
                    try {
                        for await (const event of agentEventStream) {
                            yield {
                                jsonrpc: '2.0',
                                id: requestId, // Use the original request ID for all streamed responses
                                result: event,
                            };
                        }
                    } catch (streamError: any) {
                        // If the underlying agent stream throws an error, we need to yield a JSONRPCErrorResponse.
                        // However, an AsyncGenerator is expected to yield JSONRPCResult.
                        // This indicates an issue with how errors from the agent's stream are propagated.
                        // For now, log it. The Express layer will handle the generator ending.
                        console.error(`Error in agent event stream for ${method} (request ${requestId}):`, streamError);
                        // Ideally, the Express layer should catch this and send a final error to the client if the stream breaks.
                        // Or, the agentEventStream itself should yield a final error event that gets wrapped.
                        // For now, we re-throw so it can be caught by A2AExpressApp's stream handling.
                        throw streamError;
                    }
                })();
            } else {
                // Handle non-streaming methods
                let result: any;
                switch (method) {
                    case 'message/send':
                        result = await this.requestHandler.sendMessage(params as MessageSendParams);
                        break;
                    case 'tasks/get':
                        result = await this.requestHandler.getTask(params as TaskQueryParams);
                        break;
                    case 'tasks/cancel':
                        result = await this.requestHandler.cancelTask(params as TaskIdParams);
                        break;
                    case 'tasks/pushNotificationConfig/set':
                        result = await this.requestHandler.setTaskPushNotificationConfig(
                            params as TaskPushNotificationConfig
                        );
                        break;
                    case 'tasks/pushNotificationConfig/get':
                        result = await this.requestHandler.getTaskPushNotificationConfig(
                            params as TaskIdParams
                        );
                        break;
                    default:
                        throw A2AError.methodNotFound(method);
                }
                return {
                    jsonrpc: '2.0',
                    id: requestId,
                    result: result,
                } as JSONRPCResult;
            }
        } catch (error: any) {
            const a2aError = error instanceof A2AError ? error : A2AError.internalError(error.message || 'An unexpected error occurred.');
            return {
                jsonrpc: '2.0',
                id: requestId,
                error: a2aError.toJSONRPCError(),
            } as JSONRPCErrorResponse;
        }
    }
}