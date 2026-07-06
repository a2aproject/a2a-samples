# Trace Trust Extension Specification (v1)

**URI:** `https://github.com/a2aproject/a2a-samples/tree/main/extensions/trace-trust`

## Overview
The Trace Trust Extension defines a standard middleware architecture and payload structure for validating the reputation of an incoming calling agent via the TRACE API. 

This extension operates primarily on the **Server (Receiving Agent) side**, utilizing the calling agent's verifiable identity (typically extracted from connection context or a secure passport) to determine if the task should be accepted, rate-limited, or rejected.

## Protocol Mechanics

1. **Identification:** The Server Agent extracts the caller's unique ID. In A2A, this can be retrieved from an authenticated connection, an embedded `AgentCard`, or an explicit `client_id` field via a secure passport.
2. **Reputation Query:** Before passing the `A2AMessage` to the core agent logic, a middleware interceptor calls the TRACE API `POST /v1/score` with the caller's ID.
3. **Policy Enforcement:**
    - If the score is **above** the configured minimum (e.g. `0.35`), the task proceeds to the agent core.
    - If the score is **below** the minimum, the middleware immediately rejects the message with an `Access Denied` error, preventing prompt injection or resource starvation.

## AgentCard Declaration

Agents that enforce Trace Trust may optionally declare it in their AgentCard to inform callers that their identity will be scored.

```json
{
  "uri": "https://github.com/a2aproject/a2a-samples/tree/main/extensions/trace-trust",
  "params": {
    "minimumScoreRequired": 0.35,
    "failClosed": true
  }
}
```

## Security Considerations

- **Identity Spoofing:** This extension relies on the caller ID being accurately verified by the transport layer or through cryptographic signatures (e.g. x402 or Secure Passport). TRACE scoring is only effective if the `provider_id` cannot be spoofed.
- **Fail-Closed vs Fail-Open:** When the TRACE API is unreachable, agents should default to `fail-closed` for high-value operations to prevent fallback-bypass attacks.
