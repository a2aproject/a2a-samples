# A2A Client SDK

A Java implementation of the Agent-to-Agent (A2A) protocol client SDK, providing a comprehensive framework for communicating with A2A-compliant agents and services.

## Overview

The A2A Client SDK is a pure Java library that implements the client-side functionality for the A2A protocol. It provides all necessary tools to discover, communicate with, and manage tasks with A2A-compatible agents. The included translation client examples demonstrate how to use the SDK to interact with intelligent agents.

## Key Features

### 🌐 **Complete A2A Protocol Client**
- **JSON-RPC 2.0** client implementation for all A2A operations
- **Agent Discovery** via agent card retrieval
- **Task Operations** - send, query, cancel with full lifecycle management
- **Streaming Support** - real-time task updates with event listeners
- **Error Handling** - comprehensive error management with proper A2A error codes

### 🔧 **Easy Integration**
- **Pure Java** implementation with minimal dependencies
- **Thread-safe** operations for concurrent usage
- **Builder patterns** for easy configuration
- **Configurable timeouts** and retry logic

### 📡 **HTTP Client Features**
- **Synchronous** and **asynchronous** operations
- **Connection pooling** for optimal performance
- **Custom headers** and authentication support
- **Configurable SSL/TLS** settings

### 🔄 **Streaming Support**
- **Server-Sent Events (SSE)** for real-time updates
- **Event listeners** for handling streaming responses
- **Automatic reconnection** with configurable backoff
- **Error recovery** for network interruptions

## Architecture

### Key Classes

- **`A2AClient`** - Main client class for A2A operations
- **`JSONRPCRequest`** - Request building and serialization
- **`JSONRPCResponse`** - Response parsing and validation
- **`StreamingEventListener`** - Interface for streaming event handling
- **`A2AClientException`** - A2A-specific error handling
