import {
  AgentCard,
  AgentCapabilities,
  JSONRPCRequest,
  JSONRPCResult,
  JSONRPCError,
  JSONRPCErrorResponse,
  Message,
  Task,
  TaskStatusUpdateEvent,
  TaskArtifactUpdateEvent,
  MessageSendParams,
  SendMessageResponse,
  SendStreamingMessageResponse,
  SendStreamingMessageSuccessResponse,
  TaskQueryParams,
  GetTaskResponse,
  GetTaskSuccessResponse,
  TaskIdParams,
  CancelTaskResponse,
  CancelTaskSuccessResponse,
  TaskPushNotificationConfig, // Renamed from PushNotificationConfigParams for direct schema alignment
  SetTaskPushNotificationConfigRequest,
  SetTaskPushNotificationConfigResponse,
  SetTaskPushNotificationConfigSuccessResponse,
  GetTaskPushNotificationConfigRequest,
  GetTaskPushNotificationConfigResponse,
  GetTaskPushNotificationConfigSuccessResponse,
  TaskResubscriptionRequest,
  A2AError,
  SendMessageSuccessResponse
} from '../schema.js'; // Assuming schema.ts is in the same directory or appropriately pathed

// Helper type for the data yielded by streaming methods
type A2AStreamEventData = Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent;

/**
 * A2AClient is a TypeScript HTTP client for interacting with A2A-compliant agents.
 */
export class A2AClient {
  private agentBaseUrl: string;
  private agentCardPromise: Promise<AgentCard>;
  private requestIdCounter: number = 1;
  private serviceEndpointUrl?: string; // To be populated from AgentCard after fetching

  /**
   * Constructs an A2AClient instance.
   * It initiates fetching the agent card from the provided agent baseUrl.
   * The Agent Card is expected at `${agentBaseUrl}/.well-known/agent.json`.
   * The `url` field from the Agent Card will be used as the RPC service endpoint.
   * @param agentBaseUrl The base URL of the A2A agent (e.g., https://agent.example.com).
   */
  constructor(agentBaseUrl: string) {
    this.agentBaseUrl = agentBaseUrl.replace(/\/$/, ""); // Remove trailing slash if any
    this.agentCardPromise = this._fetchAndCacheAgentCard();
  }

  /**
   * Fetches the Agent Card from the agent's well-known URI and caches its service endpoint URL.
   * This method is called by the constructor.
   * @returns A Promise that resolves to the AgentCard.
   */
  private async _fetchAndCacheAgentCard(): Promise<AgentCard> {
    const agentCardUrl = `${this.agentBaseUrl}/.well-known/agent.json`;
    try {
      const response = await fetch(agentCardUrl, {
        headers: { 'Accept': 'application/json' },
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch Agent Card from ${agentCardUrl}: ${response.status} ${response.statusText}`);
      }
      const agentCard: AgentCard = await response.json();
      if (!agentCard.url) {
        throw new Error("Fetched Agent Card does not contain a valid 'url' for the service endpoint.");
      }
      this.serviceEndpointUrl = agentCard.url; // Cache the service endpoint URL from the agent card
      console.log("ENDOPINT", this.serviceEndpointUrl);
      return agentCard;
    } catch (error) {
      console.error("Error fetching or parsing Agent Card:");
      // Allow the promise to reject so users of agentCardPromise can handle it.
      throw error;
    }
  }

  /**
   * Retrieves the Agent Card.
   * If an `agentBaseUrl` is provided, it fetches the card from that specific URL.
   * Otherwise, it returns the card fetched and cached during client construction.
   * @param agentBaseUrl Optional. The base URL of the agent to fetch the card from.
   * If provided, this will fetch a new card, not use the cached one from the constructor's URL.
   * @returns A Promise that resolves to the AgentCard.
   */
  public async getAgentCard(agentBaseUrl?: string): Promise<AgentCard> {
    if (agentBaseUrl) {
      const specificAgentBaseUrl = agentBaseUrl.replace(/\/$/, "");
      const agentCardUrl = `${specificAgentBaseUrl}/.well-known/agent.json`;
      const response = await fetch(agentCardUrl, {
        headers: { 'Accept': 'application/json' },
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch Agent Card from ${agentCardUrl}: ${response.status} ${response.statusText}`);
      }
      return await response.json() as AgentCard;
    }
    // If no specific URL is given, return the promise for the initially configured agent's card.
    return this.agentCardPromise;
  }

  /**
   * Gets the RPC service endpoint URL. Ensures the agent card has been fetched first.
   * @returns A Promise that resolves to the service endpoint URL string.
   */
  private async _getServiceEndpoint(): Promise<string> {
    if (this.serviceEndpointUrl) {
      return this.serviceEndpointUrl;
    }
    // If serviceEndpointUrl is not set, it means the agent card fetch is pending or failed.
    // Awaiting agentCardPromise will either resolve it or throw if fetching failed.
    await this.agentCardPromise;
    if (!this.serviceEndpointUrl) {
      // This case should ideally be covered by the error handling in _fetchAndCacheAgentCard
      throw new Error("Agent Card URL for RPC endpoint is not available. Fetching might have failed.");
    }
    return this.serviceEndpointUrl;
  }

  /**
   * Helper method to make a generic JSON-RPC POST request.
   * @param method The RPC method name.
   * @param params The parameters for the RPC method.
   * @returns A Promise that resolves to the RPC response.
   */
  private async _postRpcRequest<TParams, TResponse extends (JSONRPCResult<any> | JSONRPCErrorResponse)>(
    method: string,
    params: TParams
  ): Promise<TResponse> {
    const endpoint = await this._getServiceEndpoint();
    const requestId = this.requestIdCounter++;
    const rpcRequest: JSONRPCRequest = {
      jsonrpc: "2.0",
      method,
      params: params as { [key: string]: any; }, // Cast because TParams structure varies per method
      id: requestId,
    };

    const httpResponse = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json", // Expect JSON response for non-streaming requests
      },
      body: JSON.stringify(rpcRequest),
    });

    if (!httpResponse.ok) {
      let errorBodyText = '(empty or non-JSON response)';
      try {
        errorBodyText = await httpResponse.text();
        const errorJson = JSON.parse(errorBodyText);
        // If the body is a valid JSON-RPC error response, let it be handled by the standard parsing below.
        // However, if it's not even a JSON-RPC structure but still an error, throw based on HTTP status.
        if (!errorJson.jsonrpc && errorJson.error) { // Check if it's a JSON-RPC error structure
          throw new Error(`RPC error for ${method}: ${errorJson.error.message} (Code: ${errorJson.error.code}, HTTP Status: ${httpResponse.status}) Data: ${JSON.stringify(errorJson.error.data)}`);
        } else if (!errorJson.jsonrpc) {
          throw new Error(`HTTP error for ${method}! Status: ${httpResponse.status} ${httpResponse.statusText}. Response: ${errorBodyText}`);
        }
      } catch (e: any) {
        // If parsing the error body fails or it's not a JSON-RPC error, throw a generic HTTP error.
        // If it was already an error thrown from within the try block, rethrow it.
        if (e.message.startsWith('RPC error for') || e.message.startsWith('HTTP error for')) throw e;
        throw new Error(`HTTP error for ${method}! Status: ${httpResponse.status} ${httpResponse.statusText}. Response: ${errorBodyText}`);
      }
    }

    const rpcResponse = await httpResponse.json();

    if (rpcResponse.id !== requestId) {
      // This is a significant issue for request-response matching.
      console.error(`CRITICAL: RPC response ID mismatch for method ${method}. Expected ${requestId}, got ${rpcResponse.id}. This may lead to incorrect response handling.`);
      // Depending on strictness, one might throw an error here.
      // throw new Error(`RPC response ID mismatch for method ${method}. Expected ${requestId}, got ${rpcResponse.id}`);
    }

    return rpcResponse as TResponse;
  }


  /**
   * Sends a message to the agent.
   * The behavior (blocking/non-blocking) and push notification configuration
   * are specified within the `params.configuration` object.
   * Optionally, `params.message.contextId` or `params.message.taskId` can be provided.
   * @param params The parameters for sending the message, including the message content and configuration.
   * @returns A Promise resolving to SendMessageResponse, which can be a Message, Task, or an error.
   */
  public async sendMessage(params: MessageSendParams): Promise<SendMessageResponse> {
    return this._postRpcRequest<MessageSendParams, SendMessageResponse>("message/send", params);
  }

  /**
   * Sends a message to the agent and streams back responses using Server-Sent Events (SSE).
   * Push notification configuration can be specified in `params.configuration`.
   * Optionally, `params.message.contextId` or `params.message.taskId` can be provided.
   * Requires the agent to support streaming (`capabilities.streaming: true` in AgentCard).
   * @param params The parameters for sending the message.
   * @returns An AsyncGenerator yielding A2AStreamEventData (Message, Task, TaskStatusUpdateEvent, or TaskArtifactUpdateEvent).
   * The generator throws an error if streaming is not supported or if an HTTP/SSE error occurs.
   */
  public async *sendMessageStream(params: MessageSendParams): AsyncGenerator<A2AStreamEventData, void, undefined> {
    const agentCard = await this.agentCardPromise; // Ensure agent card is fetched
    if (!agentCard.capabilities?.streaming) {
      throw new Error("Agent does not support streaming (AgentCard.capabilities.streaming is not true).");
    }

    const endpoint = await this._getServiceEndpoint();
    const clientRequestId = this.requestIdCounter++; // Use a unique ID for this stream request
    const rpcRequest: JSONRPCRequest = { // This is the initial JSON-RPC request to establish the stream
      jsonrpc: "2.0",
      method: "message/stream",
      params: params as { [key: string]: any; },
      id: clientRequestId,
    };

    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "text/event-stream", // Crucial for SSE
      },
      body: JSON.stringify(rpcRequest),
    });

    if (!response.ok) {
      // Attempt to read error body for more details
      let errorBody = "";
      try {
        errorBody = await response.text();
        const errorJson = JSON.parse(errorBody);
        if (errorJson.error) {
          throw new Error(`HTTP error establishing stream for message/stream: ${response.status} ${response.statusText}. RPC Error: ${errorJson.error.message} (Code: ${errorJson.error.code})`);
        }
      } catch (e: any) {
        if (e.message.startsWith('HTTP error establishing stream')) throw e;
        // Fallback if body is not JSON or parsing fails
        throw new Error(`HTTP error establishing stream for message/stream: ${response.status} ${response.statusText}. Response: ${errorBody || '(empty)'}`);
      }
      throw new Error(`HTTP error establishing stream for message/stream: ${response.status} ${response.statusText}`);
    }
    if (!response.headers.get("Content-Type")?.startsWith("text/event-stream")) {
      // Server should explicitly set this content type for SSE.
      throw new Error("Invalid response Content-Type for SSE stream. Expected 'text/event-stream'.");
    }

    // Yield events from the parsed SSE stream.
    // Each event's 'data' field is a JSON-RPC response.
    yield* this._parseA2ASseStream<A2AStreamEventData>(response, clientRequestId);
  }

  /**
   * Sets or updates the push notification configuration for a given task.
   * Requires the agent to support push notifications (`capabilities.pushNotifications: true` in AgentCard).
   * @param params Parameters containing the taskId and the TaskPushNotificationConfig.
   * @returns A Promise resolving to SetTaskPushNotificationConfigResponse.
   */
  public async setTaskPushNotificationConfig(params: TaskPushNotificationConfig): Promise<SetTaskPushNotificationConfigResponse> {
    const agentCard = await this.agentCardPromise;
    if (!agentCard.capabilities?.pushNotifications) {
      throw new Error("Agent does not support push notifications (AgentCard.capabilities.pushNotifications is not true).");
    }
    // The 'params' directly matches the structure expected by the RPC method.
    return this._postRpcRequest<TaskPushNotificationConfig, SetTaskPushNotificationConfigResponse>(
      "tasks/pushNotificationConfig/set",
      params
    );
  }

  /**
   * Gets the push notification configuration for a given task.
   * @param params Parameters containing the taskId.
   * @returns A Promise resolving to GetTaskPushNotificationConfigResponse.
   */
  public async getTaskPushNotificationConfig(params: TaskIdParams): Promise<GetTaskPushNotificationConfigResponse> {
    // The 'params' (TaskIdParams) directly matches the structure expected by the RPC method.
    return this._postRpcRequest<TaskIdParams, GetTaskPushNotificationConfigResponse>(
      "tasks/pushNotificationConfig/get",
      params
    );
  }


  /**
   * Retrieves a task by its ID.
   * @param params Parameters containing the taskId and optional historyLength.
   * @returns A Promise resolving to GetTaskResponse, which contains the Task object or an error.
   */
  public async getTask(params: TaskQueryParams): Promise<GetTaskResponse> {
    return this._postRpcRequest<TaskQueryParams, GetTaskResponse>("tasks/get", params);
  }

  /**
   * Cancels a task by its ID.
   * @param params Parameters containing the taskId.
   * @returns A Promise resolving to CancelTaskResponse, which contains the updated Task object or an error.
   */
  public async cancelTask(params: TaskIdParams): Promise<CancelTaskResponse> {
    return this._postRpcRequest<TaskIdParams, CancelTaskResponse>("tasks/cancel", params);
  }

  /**
   * Resubscribes to a task's event stream using Server-Sent Events (SSE).
   * This is used if a previous SSE connection for an active task was broken.
   * Requires the agent to support streaming (`capabilities.streaming: true` in AgentCard).
   * @param params Parameters containing the taskId.
   * @returns An AsyncGenerator yielding A2AStreamEventData (Message, Task, TaskStatusUpdateEvent, or TaskArtifactUpdateEvent).
   */
  public async *resubscribeTask(params: TaskIdParams): AsyncGenerator<A2AStreamEventData, void, undefined> {
    const agentCard = await this.agentCardPromise;
    if (!agentCard.capabilities?.streaming) {
      throw new Error("Agent does not support streaming (required for tasks/resubscribe).");
    }

    const endpoint = await this._getServiceEndpoint();
    const clientRequestId = this.requestIdCounter++; // Unique ID for this resubscribe request
    const rpcRequest: JSONRPCRequest = { // Initial JSON-RPC request to establish the stream
      jsonrpc: "2.0",
      method: "tasks/resubscribe",
      params: params as { [key: string]: any; },
      id: clientRequestId,
    };

    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
      },
      body: JSON.stringify(rpcRequest),
    });

    if (!response.ok) {
      let errorBody = "";
      try {
        errorBody = await response.text();
        const errorJson = JSON.parse(errorBody);
        if (errorJson.error) {
          throw new Error(`HTTP error establishing stream for tasks/resubscribe: ${response.status} ${response.statusText}. RPC Error: ${errorJson.error.message} (Code: ${errorJson.error.code})`);
        }
      } catch (e: any) {
        if (e.message.startsWith('HTTP error establishing stream')) throw e;
        throw new Error(`HTTP error establishing stream for tasks/resubscribe: ${response.status} ${response.statusText}. Response: ${errorBody || '(empty)'}`);
      }
      throw new Error(`HTTP error establishing stream for tasks/resubscribe: ${response.status} ${response.statusText}`);
    }
    if (!response.headers.get("Content-Type")?.startsWith("text/event-stream")) {
      throw new Error("Invalid response Content-Type for SSE stream on resubscribe. Expected 'text/event-stream'.");
    }

    // The events structure for resubscribe is assumed to be the same as message/stream.
    // Each event's 'data' field is a JSON-RPC response.
    yield* this._parseA2ASseStream<A2AStreamEventData>(response, clientRequestId);
  }

  /**
   * Parses an HTTP response body as an A2A Server-Sent Event stream.
   * Each 'data' field of an SSE event is expected to be a JSON-RPC 2.0 Response object,
   * specifically a SendStreamingMessageResponse (or similar structure for resubscribe).
   * @param response The HTTP Response object whose body is the SSE stream.
   * @param originalRequestId The ID of the client's JSON-RPC request that initiated this stream.
   * Used to validate the `id` in the streamed JSON-RPC responses.
   * @returns An AsyncGenerator yielding the `result` field of each valid JSON-RPC success response from the stream.
   */
  private async *_parseA2ASseStream<TStreamItem>(
    response: Response,
    originalRequestId: number | string | null
  ): AsyncGenerator<TStreamItem, void, undefined> {
    if (!response.body) {
      throw new Error("SSE response body is undefined. Cannot read stream.");
    }
    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
    let buffer = ""; // Holds incomplete lines from the stream
    let eventDataBuffer = ""; // Holds accumulated 'data:' lines for the current event

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          // Process any final buffered event data if the stream ends abruptly after a 'data:' line
          if (eventDataBuffer.trim()) {
            const result = this._processSseEventData<TStreamItem>(eventDataBuffer, originalRequestId);
            yield result;
          }
          break; // Stream finished
        }

        buffer += value; // Append new chunk to buffer
        let lineEndIndex;
        // Process all complete lines in the buffer
        while ((lineEndIndex = buffer.indexOf('\n')) >= 0) {
          const line = buffer.substring(0, lineEndIndex).trim(); // Get and trim the line
          buffer = buffer.substring(lineEndIndex + 1); // Remove processed line from buffer

          if (line === "") { // Empty line: signifies the end of an event
            if (eventDataBuffer) { // If we have accumulated data for an event
              const result = this._processSseEventData<TStreamItem>(eventDataBuffer, originalRequestId);
              yield result;
              eventDataBuffer = ""; // Reset buffer for the next event
            }
          } else if (line.startsWith("data:")) {
            eventDataBuffer += line.substring(5).trimStart() + "\n"; // Append data (multi-line data is possible)
          } else if (line.startsWith(":")) {
            // This is a comment line in SSE, ignore it.
          } else if (line.includes(":")) {
            // Other SSE fields like 'event:', 'id:', 'retry:'.
            // The A2A spec primarily focuses on the 'data' field for JSON-RPC payloads.
            // For now, we don't specifically handle these other SSE fields unless required by spec.
          }
        }
      }
    } catch (error: any) {
      // Log and re-throw errors encountered during stream processing
      console.error("Error reading or parsing SSE stream:", error.message);
      throw error;
    } finally {
      reader.releaseLock(); // Ensure the reader lock is released
    }
  }

  /**
   * Processes a single SSE event's data string, expecting it to be a JSON-RPC response.
   * @param jsonData The string content from one or more 'data:' lines of an SSE event.
   * @param originalRequestId The ID of the client's request that initiated the stream.
   * @returns The `result` field of the parsed JSON-RPC success response.
   * @throws Error if data is not valid JSON, not a valid JSON-RPC response, an error response, or ID mismatch.
   */
  private _processSseEventData<TStreamItem>(
    jsonData: string,
    originalRequestId: number | string | null
  ): TStreamItem {
    if (!jsonData.trim()) {
      throw new Error("Attempted to process empty SSE event data.");
    }
    try {
      // SSE data can be multi-line, ensure it's treated as a single JSON string.
      const sseJsonRpcResponse = JSON.parse(jsonData.replace(/\n$/, '')); // Remove trailing newline if any

      // Type assertion to SendStreamingMessageResponse, as this is the expected structure for A2A streams.
      const a2aStreamResponse = sseJsonRpcResponse as SendStreamingMessageResponse;

      if (a2aStreamResponse.id !== originalRequestId) {
        // According to JSON-RPC spec, notifications (which SSE events can be seen as) might not have an ID,
        // or if they do, it should match. A2A spec implies streamed events are tied to the initial request.
        console.warn(`SSE Event's JSON-RPC response ID mismatch. Client request ID: ${originalRequestId}, event response ID: ${a2aStreamResponse.id}.`);
        // Depending on strictness, this could be an error. For now, it's a warning.
      }

      if (a2aStreamResponse.error) {
        const err = a2aStreamResponse.error as (JSONRPCError | A2AError);
        throw new Error(`SSE event contained an error: ${err.message} (Code: ${err.code}) Data: ${JSON.stringify(err.data)}`);
      }

      // Check if 'result' exists, as it's mandatory for successful JSON-RPC responses
      if (!('result' in a2aStreamResponse) || typeof (a2aStreamResponse as SendStreamingMessageSuccessResponse).result === 'undefined') {
        throw new Error(`SSE event JSON-RPC response is missing 'result' field. Data: ${jsonData}`);
      }

      const successResponse = a2aStreamResponse as SendStreamingMessageSuccessResponse;
      return successResponse.result as TStreamItem;
    } catch (e: any) {
      // Catch errors from JSON.parse or if it's an error response that was thrown by this function
      if (e.message.startsWith("SSE event contained an error") || e.message.startsWith("SSE event JSON-RPC response is missing 'result' field")) {
        throw e; // Re-throw errors already processed/identified by this function
      }
      // For other parsing errors or unexpected structures:
      console.error("Failed to parse SSE event data string or unexpected JSON-RPC structure:", jsonData, e);
      throw new Error(`Failed to parse SSE event data: "${jsonData.substring(0, 100)}...". Original error: ${e.message}`);
    }
  }
}
