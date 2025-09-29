# A2A Protocol Extension: Secure Passport (v1)

- **URI:** `https://github.com/a2aproject/a2a-samples/tree/main/samples/python/extensions/secure-passport`
- **Type:** Profile Extension / Data-Only Extension
- **Version:** 1.0.0

## Abstract

This extension enables an Agent2Agent (A2A) client to securely and optionally share a structured, verifiable contextual state—the **Secure Passport**—with the callee agent. This context is intended to transform anonymous A2A calls into trusted, context-aware partnerships.

## 1. Agent Declaration and Negotiation

An A2A Agent that is capable of **receiving** and utilizing the Secure Passport context **MUST** declare its support in its `AgentCard` under the **`extensions`** part of the `AgentCapabilities` object.

### Example AgentCard Declaration

The callee agent uses the `supportedStateKeys` array to explicitly declare which contextual data keys it understands and is optimized to use.

```json
{
  "uri": "https://github.com/a2aproject/a2a-samples/tree/main/samples/python/extensions/secure-passport",
  "params": {
    "supportedStateKeys": ["user_preferred_currency", "loyalty_tier"]
  }
}
```

## 2. Data Structure: CallerContext Payload

The `callerContext` object is the Secure Passport payload. It is **optional** and is included in the `metadata` map of a core A2A message structure.

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| **`clientId`** | `string` | Yes | The verifiable unique identifier of the calling agent. |
| **`signature`** | `string` | No | A digital signature of the entire `state` object, signed by the calling agent's private key, used for cryptographic verification of trust. |
| **`sessionId`** | `string` | No | A session or conversation identifier to maintain thread continuity. |
| **`state`** | `object` | Yes | A free-form JSON object containing the contextual data (e.g., user preferences, loyalty tier). |

### Example CallerContext Payload

```json
{
  "clientId": "a2a://orchestrator-agent.com",
  "sessionId": "travel-session-xyz",
  "signature": "MOCK-SIG-123456...",
  "state": {
    "user_preferred_currency": "GBP",
    "loyalty_tier": "Gold"
  }
}
```

## 3. Message Augmentation and Example Usage

The `CallerContext` payload is embedded directly into the `metadata` map of the A2A `Message` object. The key used **MUST** be the extension's URI: `https://github.com/a2aproject/a2a-samples/tree/main/samples/python/extensions/secure-passport`.

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
        "https://github.com/a2aproject/a2a-samples/tree/main/samples/python/extensions/secure-passport": {
          "clientId": "a2a://orchestrator-agent.com",
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
```

## 4. Implementation Notes and Best Practices

This section addresses the use of SDK helpers and conceptual implementation patterns.

### SDK Helper Methods

For development efficiency, A2A SDKs **SHOULD** provide convenience methods for this extension, such as:

* **AgentCard Utility:** A method to automatically generate the necessary JSON structure for the AgentCard declaration.
* **Attachment/Extraction:** Simple functions or methods to add (`add_secure_passport`) and retrieve (`get_secure_passport`) the payload from a message object.

### Conceptual Middleware Layer

The most robust integration for the Secure Passport involves a **middleware layer** in the A2A SDK:

* **Client Middleware:** Executes immediately before transport, automatically **attaching** the signed `CallerContext` to the message metadata.
* **Server Middleware:** Executes immediately upon receiving the message, **extracting** the `CallerContext`, performing the cryptographic verification, and injecting the resulting context object into the client's execution environment.

### Security and Callee Behavior

1. **Verification:** A callee agent **SHOULD** verify the provided **`signature`** before relying on the `state` content for high-privilege actions.
2. **Sensitive Data:** Agents **MUST NOT** include sensitive or mutable data in the `state` object unless robust, end-to-end cryptographic verification is implemented and required by the callee.
