# A2A Java Models

This module contains Java record classes translated from Go models for the A2A (Agent-to-Agent) protocol data model definitions.

## Translation Overview

All Go structs have been translated to Java records, preserving original comments and structure definitions. The main translation rules are as follows:

### Type Mappings

- Go `string` → Java `String`
- Go `*string` → Java `String` (optional fields)
- Go `int` → Java `int`
- Go `*int` → Java `Integer` (optional fields)
- Go `bool` → Java `boolean`
- Go `*bool` → Java `Boolean` (optional fields)
- Go `[]Type` → Java `List<Type>`
- Go `map[string]interface{}` → Java `Map<String, Object>`
- Go `interface{}` → Java `Object`

### Enum Types

- `TaskState` - Task state enumeration
- `ErrorCode` - Error code enumeration

### Core Models

#### File Content Related
- `FileContentBase` - Base structure for file content
- `FileContent` - File content interface (sealed interface)
- `FileContentBytes` - Bytes-based file content
- `FileContentURI` - URI-based file content

#### Message and Task Related
- `Part` - Part of a message or artifact
- `Artifact` - Task output or intermediate file
- `Message` - Message in the A2A protocol
- `Task` - A2A task
- `TaskStatus` - Task status
- `TaskHistory` - Task history

#### Event Related
- `TaskStatusUpdateEvent` - Task status update event
- `TaskArtifactUpdateEvent` - Task artifact update event

#### Agent Related
- `AgentAuthentication` - Agent authentication information
- `AgentCapabilities` - Agent capability description
- `AgentProvider` - Agent provider information
- `AgentSkill` - Agent skill definition
- `AgentCard` - Agent metadata card

#### JSON-RPC Related
- `JSONRPCMessageIdentifier` - JSON-RPC message identifier
- `JSONRPCMessage` - JSON-RPC message base structure
- `JSONRPCRequest` - JSON-RPC request
- `JSONRPCError` - JSON-RPC error
- `JSONRPCResponse` - JSON-RPC response

#### Request Parameters
- `TaskSendParams` - Parameters for sending task messages
- `TaskIDParams` - Parameters for task ID-based operations
- `TaskQueryParams` - Parameters for querying task information
- `PushNotificationConfig` - Push notification configuration
- `TaskPushNotificationConfig` - Task-specific push notification configuration

#### Concrete Request Classes
- `SendTaskRequest` - Send task request
- `GetTaskRequest` - Get task status request
- `CancelTaskRequest` - Cancel task request
- `SetTaskPushNotificationRequest` - Set task notification request
- `GetTaskPushNotificationRequest` - Get task notification configuration request
- `TaskResubscriptionRequest` - Resubscribe to task updates request
- `SendTaskStreamingRequest` - Send task streaming request

#### Response Classes
- `A2AError` - A2A protocol error
- `SendTaskResponse` - Send task response
- `SendTaskStreamingResponse` - Streaming task response
- `GetTaskResponse` - Get task response
- `CancelTaskResponse` - Cancel task response
- `GetTaskHistoryResponse` - Get task history response
- `SetTaskPushNotificationResponse` - Set task push notification response
- `GetTaskPushNotificationResponse` - Get task push notification response

## Jackson Annotations

All records use Jackson annotations for JSON serialization/deserialization:

- `@JsonProperty` - Specify JSON field names
- `@JsonInclude(JsonInclude.Include.NON_NULL)` - Exclude null value fields
- `@JsonValue` - For enum type value serialization
- `@JsonTypeInfo` and `@JsonSubTypes` - For polymorphic type handling

## Dependencies

The project uses Jackson 2.15.2 for JSON processing:

- `jackson-core`
- `jackson-annotations`
- `jackson-databind`

## Compilation

```bash
mvn compile
```

All Java records have been verified through compilation to ensure type safety and correctness. 