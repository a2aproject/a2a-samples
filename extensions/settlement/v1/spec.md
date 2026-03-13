# A2A Settlement Extension (A2A-SE) — v1

## Overview

The A2A Settlement Extension adds escrow-based token settlement to the A2A task
lifecycle. Agents declare pricing in their Agent Cards. Clients create escrow
before sending a task, and release or refund based on the terminal task state.

A2A-SE requires zero modifications to the core A2A protocol. It uses the
existing `capabilities.extensions` mechanism for Agent Card integration, and
the existing `metadata` field on Messages and Tasks for settlement context.

## Extension URI

```text
https://a2a-settlement.org/extensions/settlement/v1
```

## Agent Card Declaration

Agents that support settlement declare the extension in their Agent Card's
`capabilities.extensions` array:

```json
{
  "capabilities": {
    "extensions": [
      {
        "uri": "https://a2a-settlement.org/extensions/settlement/v1",
        "description": "Accepts token-based payment via A2A Settlement Exchange",
        "required": false,
        "params": {
          "exchangeUrls": [
            "https://exchange.a2a-settlement.org/api/v1"
          ],
          "preferredExchange": "https://exchange.a2a-settlement.org/api/v1",
          "accountIds": {
            "https://exchange.a2a-settlement.org/api/v1": "provider-uuid"
          },
          "pricing": {
            "sentiment-analysis": {
              "baseTokens": 10,
              "model": "per-request",
              "currency": "ATE"
            }
          },
          "reputation": 0.87,
          "availability": 0.95
        }
      }
    ]
  }
}
```

### Extension Params

| Field               | Type     | Required | Description                                                |
|---------------------|----------|----------|------------------------------------------------------------|
| `exchangeUrls`      | string[] | Yes      | Exchange endpoints the agent is registered on              |
| `preferredExchange` | string   | No       | The agent's preferred exchange from the list               |
| `accountIds`        | object   | Yes      | Map of exchange URL to agent's account ID on that exchange |
| `pricing`           | object   | No       | Map of skill ID to pricing configuration                   |
| `currency`          | string   | No       | Default currency (default: `ATE`)                          |
| `reputation`        | number   | No       | Agent's reputation score (0.0 – 1.0)                       |
| `availability`      | number   | No       | Agent's availability score (0.0 – 1.0)                     |

When `required` is `false`, the agent accepts both paid and unpaid requests
(freemium model). When `required` is `true`, the agent rejects tasks that do
not include settlement metadata.

### Pricing Models

| Model         | Description                              | Example                          |
|---------------|------------------------------------------|----------------------------------|
| `per-request` | Fixed cost per task invocation           | 10 tokens per sentiment analysis |
| `per-unit`    | Cost per unit of input (per 1K chars)    | 2 tokens per 1,000 characters    |
| `per-minute`  | Cost per minute of processing time       | 5 tokens per minute of compute   |
| `negotiable`  | Price determined during task negotiation | Agent proposes price in response |

## Settlement Flow Mapped to A2A TaskStates

Settlement actions map directly to existing A2A TaskState transitions. No new
task states are required.

```text
A2A TaskState              Settlement Action
─────────────              ─────────────────
SUBMITTED       ──────►    Client creates escrow on exchange
WORKING         ──────►    No action (escrow holds)
INPUT_REQUIRED  ──────►    No action (escrow holds during multi-turn)
COMPLETED       ──────►    Client releases escrow (tokens → provider)
FAILED          ──────►    Client refunds escrow (tokens → client)
CANCELED        ──────►    Client refunds escrow (tokens → client)
REJECTED        ──────►    Client refunds escrow (tokens → client)
```

## Settlement Metadata

Settlement context is passed through A2A's existing `metadata` field using a
namespaced key `a2a-se` to avoid collisions.

### Client's Initial Message

When creating a task, the client includes the escrow reference:

```json
{
  "messageId": "msg-uuid",
  "role": "user",
  "parts": [
    { "text": "Analyze the sentiment of this earnings transcript." }
  ],
  "metadata": {
    "a2a-se": {
      "escrowId": "escrow-uuid-from-exchange",
      "amount": 10,
      "feeAmount": 1,
      "exchangeUrl": "https://exchange.a2a-settlement.org/api/v1",
      "expiresAt": "2026-02-17T12:30:00Z"
    }
  }
}
```

### Provider's Task Response

The provider acknowledges the escrow in its response metadata:

```json
{
  "id": "task-uuid",
  "status": {
    "state": "TASK_STATE_WORKING"
  },
  "metadata": {
    "a2a-se": {
      "escrowId": "escrow-uuid-from-exchange",
      "settlementStatus": "acknowledged"
    }
  }
}
```

### Settlement Status Values

| Status         | Meaning                                            |
|----------------|----------------------------------------------------|
| `pending`      | Escrow created, awaiting agent acknowledgment      |
| `acknowledged` | Agent confirmed receipt of escrow reference        |
| `review`       | Task completed, requester reviewing before release |
| `released`     | Tokens transferred to provider                     |
| `refunded`     | Tokens returned to requester                       |
| `expired`      | Escrow TTL exceeded without resolution             |
| `disputed`     | Transaction flagged by either party                |

## Settlement Exchange API

The settlement exchange is an external REST API that manages accounts, escrow,
and token balances. The exchange is an **interface**: any conforming
implementation (hosted, self-hosted, on-chain) can serve as the settlement
rail.

### Core Endpoints

| Method | Path                     | Description                                                           |
|--------|--------------------------|-----------------------------------------------------------------------|
| `POST` | `/exchange/escrow`       | Create an escrow                                                      |
| `POST` | `/exchange/release`      | Release escrowed tokens to provider. Body: `{"escrow_id": "<id>"}`    |
| `POST` | `/exchange/refund`       | Refund escrowed tokens to requester. Body: `{"escrow_id": "<id>"}`    |
| `POST` | `/exchange/dispute`      | Flag an escrow as disputed. Body: `{"escrow_id": "<id>"}`             |
| `GET`  | `/exchange/escrows/{id}` | Look up an escrow by ID                                               |
| `GET`  | `/exchange/balance`      | Get agent's token balance                                             |

### Batch Escrow for Pipelines

Multi-step workflows can create all escrows atomically with dependency ordering:

```json
{
  "group_id": "pipeline-001",
  "escrows": [
    {
      "provider_id": "translator-agent",
      "amount": 10,
      "task_type": "translate"
    },
    {
      "provider_id": "sentiment-agent",
      "amount": 15,
      "task_type": "sentiment",
      "depends_on": ["$0"]
    }
  ]
}
```

Values in `depends_on` use positional references (`$0`, `$1`, ...) referring to
other escrows in the same batch by their zero-based index. The field models
sequential dependencies: an escrow cannot be released until all upstream escrows
have been released. When an upstream escrow is refunded, all downstream escrows
are automatically cascade-refunded.

## Extension Activation

Clients activate the settlement extension using the `A2A-Extensions` HTTP
header:

```http
POST /agents/provider HTTP/1.1
A2A-Extensions: https://a2a-settlement.org/extensions/settlement/v1
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "message/send",
  "id": "1",
  "params": {
    "message": {
      "messageId": "msg-1",
      "role": "user",
      "parts": [{"text": "Analyze this text"}],
      "metadata": {
        "a2a-se": {
          "escrowId": "esc-uuid",
          "amount": 10,
          "exchangeUrl": "https://exchange.a2a-settlement.org/api/v1"
        }
      }
    }
  }
}
```

## Client Workflow

1. **Discover** provider via Agent Card; check for settlement extension URI.
2. **Negotiate exchange** — intersect `exchangeUrls` with client's exchanges.
3. **Create escrow** on the selected exchange.
4. **Send A2A message** with `a2a-se` metadata containing the `escrowId`.
5. **On terminal state** — release (COMPLETED) or refund (FAILED/CANCELED/REJECTED).

## Provider Workflow

1. **Declare** settlement extension in Agent Card with pricing.
2. **On incoming message** — read `metadata["a2a-se"]["escrowId"]`.
3. **Verify escrow** by calling `GET /exchange/escrows/{id}` on the exchange.
4. **Execute task** normally via A2A.
5. Requester handles release/refund based on task outcome.

## Security Considerations

- All exchange endpoints require Bearer token authentication.
- Escrow creation supports idempotency keys to prevent duplicate holds.
- Escrows have configurable TTL (default 30 minutes) with automatic expiration.
- Disputes freeze the escrow until operator resolution.
- The extension MUST NOT bypass the agent's primary security controls.

## Reference Implementation

- Specification: <https://github.com/a2a-settlement/a2a-settlement/blob/main/SPEC.md>
- Python SDK: `pip install a2a-settlement`
- TypeScript SDK: `npm install @a2a-settlement/sdk`
- Live exchange: <https://exchange.a2a-settlement.org/api/v1>
- Live stats: <https://exchange.a2a-settlement.org/api/v1/stats>
