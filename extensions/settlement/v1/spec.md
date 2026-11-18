# Settlement Extension

<!-- markdownlint-disable MD013 -->

## Overview

This extension adds escrow-based payment to the A2A task lifecycle. Agents
declare pricing in their AgentCard. Clients create an escrow on a settlement
exchange before sending a task, and release or refund the escrow based on the
terminal task state.

The extension requires zero modifications to the core A2A protocol. It uses
the existing `capabilities.extensions` mechanism for AgentCard integration and
the existing `metadata` field on `Message` objects for settlement context.

## Extension URI

The URI of this extension is
`https://github.com/a2aproject/a2a-samples/extensions/settlement/v1`.

This is the only URI accepted for this extension.

## AgentCard Declaration

Agents that support settlement declare the extension in their AgentCard's
`capabilities.extensions` array:

```json
{
  "capabilities": {
    "extensions": [
      {
        "uri": "https://github.com/a2aproject/a2a-samples/extensions/settlement/v1",
        "description": "Accepts escrow-based payment via a settlement exchange",
        "required": false,
        "params": {
          "exchangeUrls": ["https://exchange.example.com/api/v1"],
          "accountIds": {
            "https://exchange.example.com/api/v1": "provider-account-id"
          },
          "pricing": {
            "sentiment-analysis": {
              "baseTokens": 10,
              "model": "per-request"
            }
          }
        }
      }
    ]
  }
}
```

### Extension Params

- `exchangeUrls` (string array, required): exchange endpoints the agent is
  registered on.
- `accountIds` (object, required): map of exchange URL to the agent's account
  ID on that exchange.
- `pricing` (object, optional): map of skill ID to pricing configuration.

When `required` is `false`, the agent accepts both paid and unpaid requests.
When `required` is `true`, the agent rejects tasks that activate the extension
but do not include settlement metadata.

### Pricing Models

| Model         | Description                                |
|---------------|--------------------------------------------|
| `per-request` | Fixed cost per task invocation             |
| `per-unit`    | Cost per unit of input (e.g. per 1K chars) |
| `per-minute`  | Cost per minute of processing time         |
| `negotiable`  | Price determined during task negotiation   |

## Settlement Flow Mapped to A2A TaskStates

Settlement actions map directly onto existing A2A `TaskState` transitions. No
new task states are required.

```text
A2A TaskState              Settlement Action
─────────────              ─────────────────
SUBMITTED       ──────►    Client creates escrow on exchange
WORKING         ──────►    No action (escrow holds)
INPUT_REQUIRED  ──────►    No action (escrow holds during multi-turn)
COMPLETED       ──────►    Client releases escrow (payment to provider)
FAILED          ──────►    Client refunds escrow (funds back to client)
CANCELED        ──────►    Client refunds escrow (funds back to client)
REJECTED        ──────►    Client refunds escrow (funds back to client)
```

The release decision belongs to the client (the party that funded the escrow).
Implementations MUST NOT allow the provider to trigger release of its own
payment.

## Message Metadata Fields

Settlement context is stored in the metadata of the client's initial
`Message`, under fields namespaced by the extension URI path:

Metadata fields are suffixed on
`github.com/a2aproject/a2a-samples/extensions/settlement/v1/`:

- `escrow_id` (string): escrow identifier from the exchange.
- `amount` (number): escrowed amount.
- `exchange_url` (string): exchange the escrow was created on.

Example client message:

```json
{
  "message_id": "msg-1",
  "role": "ROLE_USER",
  "content": [{ "text": "Analyze the sentiment of this transcript." }],
  "metadata": {
    "github.com/a2aproject/a2a-samples/extensions/settlement/v1/escrow_id": "escrow-123",
    "github.com/a2aproject/a2a-samples/extensions/settlement/v1/amount": 10,
    "github.com/a2aproject/a2a-samples/extensions/settlement/v1/exchange_url": "https://exchange.example.com/api/v1"
  }
}
```

## Settlement Exchange Interface

The settlement exchange is an external REST API that manages accounts, escrow,
and balances. The exchange is an **interface**: any conforming implementation
(hosted, self-hosted, on-chain) can serve as the settlement rail. This
specification does not define or endorse a specific exchange deployment.

### Required Endpoints

- `POST /exchange/escrow`: create an escrow.
  Body: `{"provider_id": "<id>", "amount": <n>}`.
- `GET /exchange/escrows/{id}`: look up an escrow by ID.
- `POST /exchange/release`: release escrowed funds to provider.
  Body: `{"escrow_id": "<id>"}`.
- `POST /exchange/refund`: refund escrowed funds to requester.
  Body: `{"escrow_id": "<id>"}`.

An escrow object has at minimum: `escrow_id`, `provider_id`, `amount`, and
`status` (one of `held`, `released`, `refunded`).

Release and refund MUST be idempotent-safe: a second release or refund of an
escrow already in a terminal status MUST be rejected, not repeated.

## Extension Activation

Clients indicate their desire to use settlement by specifying the
[Extension URI](#extension-uri) via the transport-defined extension activation
mechanism. For JSON-RPC and HTTP transports, this is the `X-A2A-Extensions`
HTTP header. For gRPC, this is the `X-A2A-Extensions` metadata value.

## Client Workflow

1. **Discover** provider via AgentCard; check for the settlement extension URI.
2. **Select exchange** — intersect `exchangeUrls` with the exchanges the
   client has an account on.
3. **Create escrow** on the selected exchange for the provider's declared
   price.
4. **Send A2A message** with the settlement metadata fields and the extension
   activated.
5. **On terminal state** — release (COMPLETED) or refund
   (FAILED / CANCELED / REJECTED).

## Provider Workflow

1. **Declare** the settlement extension in the AgentCard with pricing.
2. **On incoming message** — read the `escrow_id` metadata field.
3. **Verify escrow** by calling `GET /exchange/escrows/{id}` on the exchange:
   the escrow exists, is in `held` status, names this agent as provider, and
   matches the declared amount.
4. **Execute task** normally via A2A.
5. The client handles release/refund based on the task outcome.

## Security Considerations

- Exchange endpoints require Bearer token authentication.
- Escrow IDs arriving in message metadata are untrusted input and MUST be
  validated before use in exchange API calls.
- Providers MUST verify escrow status, provider binding, and amount before
  executing paid work; a held escrow naming a different provider or a
  different amount is a rejection.
- Providers SHOULD track recently seen escrow IDs and reject reuse of an
  escrow across multiple tasks.
- The release decision stays with the client; provider-initiated release of
  the provider's own payment is out of scope by design.
- The extension MUST NOT bypass the agent's primary security controls.
