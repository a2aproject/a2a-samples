// === JSON-RPC Base Structures ===

/**
 * Base interface for all JSON-RPC messages (Requests and Responses).
 */
export interface JSONRPCMessage {
  id?: number | string | null;
  readonly jsonrpc: "2.0";
}

/**
 * Represents a JSON-RPC request object base structure.
 */
export interface JSONRPCRequest extends JSONRPCMessage {
  method: string;
  params?: { [key: string]: any };
}

/**
 * Represents a JSON-RPC 2.0 Error object.
 */
export interface JSONRPCError {
  code: number;
  message: string;
  data?: any; // Reverted from generic D to any
}

/**
 * Represents a JSON-RPC 2.0 Result object (for successful responses).
 * @template R Type of the result field.
 */
export interface JSONRPCResult<R = any> extends JSONRPCMessage {
  result: R;
  error?: never;
}

/**
 * Represents a JSON-RPC 2.0 Error Response object.
 */
export interface JSONRPCErrorResponse extends JSONRPCMessage {
  result?: never;
  error: JSONRPCError | A2AError; // Uses non-generic JSONRPCError and A2AError
}

// === Core A2A Data Structures ===

export enum TaskState {
  Submitted = "submitted",
  Working = "working",
  InputRequired = "input-required",
  Completed = "completed",
  Canceled = "canceled",
  Failed = "failed",
  Rejected = "rejected",
  AuthRequired = "auth-required",
  Unknown = "unknown",
}

export interface AgentCapabilities {
  streaming?: boolean;
  pushNotifications?: boolean;
  stateTransitionHistory?: boolean;
}

export interface AgentProvider {
  organization: string;
  url: string;
}

export interface AgentSkill {
  id: string;
  name: string;
  description: string;
  tags: string[];
  examples?: string[];
  inputModes?: string[];
  outputModes?: string[];
}

// Security Scheme types
export interface SecuritySchemeBase {
  description?: string;
}

export interface APIKeySecurityScheme extends SecuritySchemeBase {
  type: "apiKey";
  in: "query" | "header" | "cookie";
  name: string;
}

export interface HTTPAuthSecurityScheme extends SecuritySchemeBase {
  type: "http";
  scheme: string;
  bearerFormat?: string;
}

export interface OAuthFlows {
  authorizationCode?: AuthorizationCodeOAuthFlow;
  clientCredentials?: ClientCredentialsOAuthFlow;
  implicit?: ImplicitOAuthFlow;
  password?: PasswordOAuthFlow;
}

export interface AuthorizationCodeOAuthFlow {
  authorizationUrl: string;
  tokenUrl: string;
  refreshUrl?: string;
  scopes: { [name: string]: string };
}

export interface ClientCredentialsOAuthFlow {
  tokenUrl: string;
  refreshUrl?: string;
  scopes: { [name: string]: string };
}

export interface ImplicitOAuthFlow {
  authorizationUrl: string;
  refreshUrl?: string;
  scopes: { [name: string]: string };
}

export interface PasswordOAuthFlow {
  tokenUrl: string;
  refreshUrl?: string;
  scopes: { [name: string]: string };
}

export interface OAuth2SecurityScheme extends SecuritySchemeBase {
  type: "oauth2";
  flows: OAuthFlows;
}

export interface OpenIdConnectSecurityScheme extends SecuritySchemeBase {
  type: "openIdConnect";
  openIdConnectUrl: string;
}

export type SecurityScheme =
  | APIKeySecurityScheme
  | HTTPAuthSecurityScheme
  | OAuth2SecurityScheme
  | OpenIdConnectSecurityScheme;

export interface AgentCard {
  name: string;
  description: string;
  url: string;
  provider?: AgentProvider;
  version: string;
  documentationUrl?: string;
  capabilities: AgentCapabilities;
  securitySchemes?: { [scheme: string]: SecurityScheme };
  security?: { [scheme: string]: string[] }[];
  defaultInputModes: string[];
  defaultOutputModes: string[];
  skills: AgentSkill[];
  supportsAuthenticatedExtendedCard?: boolean;
}

export interface PartBase {
  metadata?: { [key: string]: any };
}

export interface TextPart extends PartBase {
  kind: "text";
  text: string;
}

export interface FileBase {
  name?: string;
  mimeType?: string;
}

export interface FileWithBytes extends FileBase {
  bytes: string;
  uri?: never;
}

export interface FileWithUri extends FileBase {
  uri: string;
  bytes?: never;
}

export interface FilePart extends PartBase {
  kind: "file";
  file: FileWithBytes | FileWithUri;
}

export interface DataPart extends PartBase {
  kind: "data";
  data: { [key: string]: any };
}

export type Part = TextPart | FilePart | DataPart;

export interface Artifact {
  artifactId: string;
  name?: string;
  description?: string;
  parts: Part[];
  metadata?: { [key: string]: any };
}

export interface Message {
  role: "user" | "agent";
  parts: Part[];
  metadata?: { [key: string]: any };
  referenceTaskIds?: string[];
  messageId: string;
  taskId?: string;
  contextId?: string;
  kind: "message";
}

export interface TaskStatus {
  state: TaskState;
  message?: Message;
  timestamp?: string;
}

export interface Task {
  id: string;
  contextId: string;
  status: TaskStatus;
  history?: Message[];
  artifacts?: Artifact[];
  metadata?: { [key: string]: any };
  kind: "task";
}

export interface TaskStatusUpdateEvent {
  taskId: string;
  contextId: string;
  kind: "status-update";
  status: TaskStatus;
  final: boolean;
  metadata?: { [key: string]: any };
}

export interface TaskArtifactUpdateEvent {
  taskId: string;
  contextId: string;
  kind: "artifact-update";
  artifact: Artifact;
  append?: boolean;
  lastChunk?: boolean;
  metadata?: { [key: string]: any };
}


// === Error Types (Standard and A2A from types.ts) ===

export interface JSONParseError extends JSONRPCError {
  code: -32700;
  message: string;
}

export interface InvalidRequestError extends JSONRPCError {
  code: -32600;
  message: string;
}

export interface MethodNotFoundError extends JSONRPCError {
  code: -32601;
  message: string;
}

export interface InvalidParamsError extends JSONRPCError {
  code: -32602;
  message: string;
}

export interface InternalError extends JSONRPCError {
  code: -32603;
  message: string;
}

export interface TaskNotFoundError extends JSONRPCError {
  code: -32001;
  message: string;
}

export interface TaskNotCancelableError extends JSONRPCError {
  code: -32002;
  message: string;
}

export interface PushNotificationNotSupportedError extends JSONRPCError {
  code: -32003;
  message: string;
}

export interface UnsupportedOperationError extends JSONRPCError {
  code: -32004;
  message: string;
}

export interface ContentTypeNotSupportedError extends JSONRPCError {
  code: -32005;
  message: string;
}

export interface InvalidAgentResponseError extends JSONRPCError {
  code: -32006;
  message: string;
}

/**
 * Union of all A2A specific and standard JSON-RPC errors.
 */
export type A2AError =
  | JSONParseError
  | InvalidRequestError
  | MethodNotFoundError
  | InvalidParamsError
  | InternalError
  | TaskNotFoundError
  | TaskNotCancelableError
  | PushNotificationNotSupportedError
  | UnsupportedOperationError
  | ContentTypeNotSupportedError
  | InvalidAgentResponseError;

// === Push Notifications ===

export interface PushNotificationAuthenticationInfo {
  schemes: string[];
  credentials?: string;
}

export interface PushNotificationConfig {
  url: string;
  token?: string;
  authentication?: PushNotificationAuthenticationInfo;
}

export interface TaskPushNotificationConfig {
  taskId: string;
  pushNotificationConfig: PushNotificationConfig;
}

// ================================================================= A2A Request Parameter Types
// =================================================================

export interface TaskIdParams {
  id: string;
  metadata?: { [key: string]: any };
}

export interface TaskQueryParams extends TaskIdParams {
  historyLength?: number;
}

export interface MessageSendConfiguration {
  acceptedOutputModes: string[];
  historyLength?: number;
  pushNotificationConfig?: PushNotificationConfig;
  blocking?: boolean;
}

export interface MessageSendParams {
  message: Message;
  configuration?: MessageSendConfiguration;
  metadata?: { [key: string]: any };
}


// === A2A Request Interfaces ===

export interface SendMessageRequest extends JSONRPCRequest {
  method: "message/send";
  params: MessageSendParams;
}

export interface SendStreamingMessageRequest extends JSONRPCRequest {
  method: "message/stream";
  params: MessageSendParams;
}

export interface GetTaskRequest extends JSONRPCRequest {
  method: "tasks/get";
  params: TaskQueryParams;
}

export interface CancelTaskRequest extends JSONRPCRequest {
  method: "tasks/cancel";
  params: TaskIdParams;
}

export interface SetTaskPushNotificationConfigRequest extends JSONRPCRequest {
  method: "tasks/pushNotificationConfig/set";
  params: TaskPushNotificationConfig;
}

export interface GetTaskPushNotificationConfigRequest extends JSONRPCRequest {
  method: "tasks/pushNotificationConfig/get";
  params: TaskIdParams;
}

export interface TaskResubscriptionRequest extends JSONRPCRequest {
  method: "tasks/resubscribe";
  params: TaskIdParams;
}


// === A2A Response Interfaces ===

// --- SendMessage ---
export interface SendMessageSuccessResponse extends JSONRPCResult<Message | Task> { }
export type SendMessageResponse = SendMessageSuccessResponse | JSONRPCErrorResponse;

// --- SendStreamingMessage ---
export interface SendStreamingMessageSuccessResponse
  extends JSONRPCResult<Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent> { }
export type SendStreamingMessageResponse =
  | SendStreamingMessageSuccessResponse
  | JSONRPCErrorResponse;

// --- GetTask ---
export interface GetTaskSuccessResponse extends JSONRPCResult<Task> { }
export type GetTaskResponse = GetTaskSuccessResponse | JSONRPCErrorResponse;

// --- CancelTask ---
export interface CancelTaskSuccessResponse extends JSONRPCResult<Task> { }
export type CancelTaskResponse = CancelTaskSuccessResponse | JSONRPCErrorResponse;

// --- SetTaskPushNotificationConfig ---
export interface SetTaskPushNotificationConfigSuccessResponse
  extends JSONRPCResult<TaskPushNotificationConfig> { }
export type SetTaskPushNotificationConfigResponse =
  | SetTaskPushNotificationConfigSuccessResponse
  | JSONRPCErrorResponse;

// --- GetTaskPushNotificationConfig ---
export interface GetTaskPushNotificationConfigSuccessResponse
  extends JSONRPCResult<TaskPushNotificationConfig> { }
export type GetTaskPushNotificationConfigResponse =
  | GetTaskPushNotificationConfigSuccessResponse
  | JSONRPCErrorResponse;


// === Union Types for A2A Requests/Responses ===

export type A2ARequest =
  | SendMessageRequest
  | SendStreamingMessageRequest
  | GetTaskRequest
  | CancelTaskRequest
  | SetTaskPushNotificationConfigRequest
  | GetTaskPushNotificationConfigRequest
  | TaskResubscriptionRequest;

/**
 * Represents any valid JSON-RPC response defined in the A2A protocol.
 */
export type A2AResponse =
  | SendMessageResponse
  | SendStreamingMessageResponse
  | GetTaskResponse
  | CancelTaskResponse
  | SetTaskPushNotificationConfigResponse
  | GetTaskPushNotificationConfigResponse
  | JSONRPCErrorResponse; // Catch-all for other error responses