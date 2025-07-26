# A2A Java Sample Project

This project is a Java implementation example of the Agent-to-Agent (A2A) protocol, providing complete client and server SDKs, along with an AI-powered translation service demonstration application.

## Project Architecture

This project uses a Maven multi-module architecture, containing the following three core modules:

```
samples/java/
├── model/          # A2A Protocol Data Models
├── server/         # A2A Server SDK & Translation Service
├── client/         # A2A Client SDK & Example Code
└── pom.xml         # Parent Maven Configuration File
```

### Module Details

#### 🎯 **Model Module** (`model/`)
Core data models for the A2A protocol, providing complete data structures for JSON-RPC 2.0 and A2A protocol:

- **Message Models**: `Message`, `Part`, `TextPart`, `Artifact`
- **Task Models**: `Task`, `TaskStatus`, `TaskState`
- **Agent Models**: `AgentCard`, `AgentCapabilities`, `AgentSkill`
- **JSON-RPC Models**: `JSONRPCRequest`, `JSONRPCResponse`, `JSONRPCError`
- **Event Models**: `TaskStatusUpdateEvent`, `TaskArtifactUpdateEvent`

#### 🚀 **Server Module** (`server/`)
Spring Boot-based A2A server SDK, integrated with Spring AI framework:

- **Core Components**:
  - `A2AServer`: Main server class managing agent behavior
  - `A2AController`: REST controller implementing A2A protocol endpoints
  - `TaskHandler`: Task processing interface
  - `A2AServerConfiguration`: AI translation bot configuration

- **Key Features**:
  - Complete JSON-RPC 2.0 support
  - Agent card publishing (`/.well-known/agent.json`)
  - Task management (send, query, cancel)
  - Streaming response support (Server-Sent Events)
  - Spring AI integration supporting OpenAI and other models

#### 📱 **Client Module** (`client/`)
Pure Java A2A client SDK with translation client examples:

- **Core Components**:
  - `A2AClient`: Main client class handling all A2A operations
  - `StreamingEventListener`: Streaming event listener interface
  - `A2AClientException`: A2A-specific exception handling
  - `A2AClientExample`: Complete translation client example

- **Key Features**:
  - JSON-RPC 2.0 client implementation
  - Agent discovery and capability querying
  - Synchronous/asynchronous task operations
  - Streaming response handling
  - Connection pooling and error recovery

## Core Functionality Implementation

### 🤖 AI Translation Service

The project implements an intelligent translation agent supporting multi-language translation:

**Translation Logic**:
- Chinese → English
- English → Chinese  
- Other languages → English

**Technical Features**:
- Based on Spring AI ChatClient
- Supports OpenAI, Azure OpenAI, and other models
- Context-aware natural language translation
- Real-time streaming responses

### 🔄 A2A Protocol Implementation

Complete implementation of A2A protocol specifications:

**Core Operations**:
- `message/send`: Send task messages
- `tasks/get`: Query task status
- `tasks/cancel`: Cancel task execution

**Protocol Features**:
- JSON-RPC 2.0 communication
- Agent capability discovery
- Task status tracking
- Streaming event push
- Standardized error codes

### 📡 Communication Mechanisms

**Synchronous Communication**: 
- HTTP POST `/a2a` - Standard JSON-RPC requests
- HTTP GET `/.well-known/agent.json` - Agent information retrieval

**Streaming Communication**:
- HTTP POST `/a2a/stream` - Server-Sent Events
- Real-time task status updates
- Automatic reconnection and error recovery

## How to Run

### Requirements

- **Java**: 17 or higher

### Step 1: Compile the Project

Execute compilation in the project root directory:

```bash
cd samples/java
./mvnw clean install -DskipTests
```

### Step 2: Configure Environment Variables

Set AI model-related environment variables (required for translation functionality):

```bash
# OpenAI Configuration
export OPENAI_API_KEY="your-openai-api-key"
export OPENAI_BASE_URL="https://api.openai.com"
export OPENAI_CHAT_MODEL="gpt-4o"

# Or GCP OpenAI Configuration
export OPENAI_API_KEY="your-gcp-api-key"
export OPENAI_BASE_URL="https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/endpoints/openapi"
export OPENAI_CHAT_MODEL="gemini-2.5-pro-preview-05-06"
```

### Step 3: Start the Translation Server

Start the A2A translation server:

```bash
cd server
../mvnw spring-boot:run
```

The server will start at `http://localhost:8080`, providing the following endpoints:
- `http://localhost:8080/.well-known/agent.json` - Agent information
- `http://localhost:8080/a2a` - A2A protocol endpoint
- `http://localhost:8080/a2a/stream` - Streaming endpoint

### Step 4: Run the Translation Client

In a new terminal window, run the client example:

```bash
cd client
../mvnw exec:java -Dexec.mainClass="com.google.a2a.client.A2AClientExample"
```

## API Usage Examples

### Get Agent Information

```bash
curl -X GET http://localhost:8080/.well-known/agent.json \
  -H "Accept: application/json"
```

### Send Translation Task

```bash
curl -X POST http://localhost:8080/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "request-1",
    "method": "message/send",
    "params": {
      "id": "translation-task-1",
      "message": {
        "messageId": "msg-1",
        "kind": "message",
        "role": "user",
        "parts": [
          {
            "kind": "text",
            "text": "Hello, world!"
          }
        ]
      }
    }
  }'
```

### Streaming Translation

```bash
curl -X POST http://localhost:8080/a2a/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": "stream-request-1",
    "method": "message/send",
    "params": {
      "id": "streaming-translation-task",
      "message": {
        "messageId": "stream-msg-1",
        "kind": "message",
        "role": "user",
        "parts": [
          {
            "kind": "text",
            "text": "Hello world!"
          }
        ]
      }
    }
  }'
```

## Extension Development

### Adding New Agent Skills

1. Define new `AgentSkill` in `A2AServerConfiguration`
2. Implement corresponding `TaskHandler` logic
3. Update the agent card's skill list


## Disclaimer
Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.  Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.
