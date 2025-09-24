# A2A Protocol Extension: Secure Passport (v1)

- **URI:** `https://a2aprotocol.ai/ext/secure-passport/v1`
- **Type:** Profile Extension / Data-Only Extension
- **Version:** 1.0.0

## Abstract

This extension enables an Agent2Agent (A2A) client to securely and optionally share a structured, verifiable contextual state—the **Secure Passport**—with the callee agent. This context is intended to transform anonymous A2A calls into trusted, context-aware partnerships.

## 1. Agent Declaration and Negotiation

An A2A Agent that is capable of **receiving** and utilizing the Secure Passport context **MUST** declare its support in its `AgentCard` under the `AgentCapabilities` object.

### Example AgentCard Declaration

The callee agent uses the `supportedStateKeys` array to explicitly declare which contextual data keys it understands and is optimized to use.

```json
{
  "uri": "https://a2aprotocol.ai/ext/secure-passport/v1",
  "params": {
    "receivesCallerContext": true,
    "supportedStateKeys": ["user_preferred_currency", "loyalty_tier"]
  }
}

## 2. Data Structure: CallerContext Payload

The `callerContext` object is the Secure Passport payload. It is **optional** and is included in the `metadata` map of a core A2A message structure.

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| **`agentId`** | `string` | Yes | The verifiable unique identifier of the calling agent. |
| **`signature`** | `string` | No | A digital signature of the entire `state` object, signed by the calling agent's private key, used for cryptographic verification of trust. |
| **`sessionId`** | `string` | No | A session or conversation identifier to maintain thread continuity. |
| **`state`** | `object` | Yes | A free-form JSON object containing the contextual data (e.g., user preferences, loyalty tier). |

### Example CallerContext Payload

```json
{
  "agentId": "a2a://orchestrator-agent.com",
  "sessionId": "travel-session-xyz",
  "signature": "MOCK-SIG-123456...",
  "state": {
    "user_preferred_currency": "GBP",
    "loyalty_tier": "Gold"
  }
}

## 3. Message Augmentation and Example Usage

The `CallerContext` payload is embedded directly into the `metadata` map of the A2A `Message` object. The key used **MUST** be the extension's URI: `https://a2aprotocol.ai/ext/secure-passport/v1`.

### Example A2A Message Request (Simplified)

This example shows the request body for an A2A `tasks/send` RPC call.

```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "method": "tasks/send",
  "params": {
    "message": {
      "messageId": "msg-456",
      "role": "user",
      "parts": [
        {"kind": "text", "content": "Book a flight for me."}
      ],
      "metadata": {
        "[https://a2aprotocol.ai/ext/secure-passport/v1](https://a2aprotocol.ai/ext/secure-passport/v1)": {
          "agentId": "a2a://orchestrator-agent.com",
          "sessionId": "travel-session-xyz",
          "signature": "MOCK-SIG-123456...",
          "state": {
            "user_preferred_currency": "GBP",
            "loyalty_tier": "Gold"
          }
        }
      }
    }
  }
}


