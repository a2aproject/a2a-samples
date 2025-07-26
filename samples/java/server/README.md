# A2A Server SDK

A Java implementation of the Agent-to-Agent (A2A) protocol server SDK, built with Spring Boot and Spring AI. This SDK provides a complete framework for building A2A-compliant agents and services.

## Overview

The A2A Server SDK is a comprehensive Java library that implements the A2A protocol server-side functionality. It provides all the necessary components to build agents that can communicate with other A2A-compatible systems. The included translation bot is a demonstration of how to use the SDK to build intelligent agents.

## Key Features

### 🚀 **Complete A2A Protocol Implementation**
- **JSON-RPC 2.0** support for all A2A operations
- **Agent Card** publishing at `/.well-known/agent.json`
- **Task Management** - send, query, cancel operations
- **Streaming Support** - real-time task updates via Server-Sent Events
- **Error Handling** - comprehensive error management with proper codes

### 🔧 **Spring Boot Integration**
- Auto-configuration for easy setup
- RESTful API endpoints with proper HTTP status codes
- Built-in validation and serialization
- Health checks and metrics endpoints

### 🤖 **AI Integration Ready**
- **Spring AI** integration for AI model connectivity
- **ChatClient** abstraction for easy AI service integration
- Support for OpenAI, Azure OpenAI, and other providers
- Configurable model parameters and prompts

## Architecture

### Key Classes

- **`A2AServer`** - Main server class managing agent behavior
- **`A2AController`** - REST controller implementing A2A endpoints
- **`TaskHandler`** - Interface for implementing custom agent logic
- **`A2AServerConfiguration`** - Configuration class for agent setup

## API Endpoints

### Agent Card Endpoint
```http
GET /.well-known/agent.json
Accept: application/json
```

Returns the agent's capabilities and metadata.

### Task Operations
```http
POST /a2a
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": "request-1",
  "method": "message/send",
  "params": {
    "id": "task-1",
    "message": {
      "messageId": "msg-1",
      "kind": "message",
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "Hello, agent!"
        }
      ]
    }
  }
}
```

### Streaming Support
```http
POST /a2a/stream
Content-Type: application/json
Accept: text/event-stream
```
