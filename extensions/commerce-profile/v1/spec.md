# A2A Commerce Profile Extension (v1)

- **URI:** `https://github.com/a2aproject/a2a-samples/extensions/commerce-profile/v1`
- **Type:** Profile Extension / Metadata Extension
- **Version:** 0.1.0

## Abstract

This extension defines an optional profile for paid A2A capability execution.
It lets an agent advertise where a buyer can fetch current commerce terms, then
lets the buyer attach a payment proof to the normal A2A message metadata.

The profile does not replace A2A messaging, discovery, authentication, or task
state. It only standardizes the points where commerce metadata can be declared,
attached, and reconciled.

## Goals

- Keep the normal A2A `message/send` flow unchanged.
- Advertise commerce support through `AgentCapabilities.extensions`.
- Resolve dynamic pricing and settlement terms from a descriptor URL.
- Carry payment proof in A2A message metadata.
- Return a receipt identifier that can be reconciled out of band.

## Non-Goals

- Requiring a specific payment provider, chain, token, or processor.
- Requiring all A2A agents to support paid execution.
- Defining marketplace ranking, reputation, or identity resolution.
- Replacing A2A authentication, authorization, or transport security.

## 1. Agent Card Declaration

An agent that supports this profile SHOULD declare it in the Agent Card
`capabilities.extensions` array.

```json
{
    "uri": "https://github.com/a2aproject/a2a-samples/extensions/commerce-profile/v1",
    "params": {
        "descriptorUrl": "https://seller.example.com/.well-known/commerce-profile.json",
        "supportedSettlement": ["x402", "usdc-base", "invoice"],
        "receiptUrl": "https://seller.example.com/receipts/{receiptId}"
    }
}
```

The `descriptorUrl` points to the current commerce descriptor for the service.
The descriptor MAY use an Agoragentic Commerce Protocol (ACP) shape or another
provider-specific schema. A buyer MUST treat the descriptor as untrusted input.

## 2. Commerce Descriptor

The commerce descriptor describes the paid capability and current terms. It is
separate from the Agent Card so that price, settlement availability, and rate
limits can change without republishing the whole card.

The descriptor SHOULD include:

| Field          | Required | Description                                      |
| -------------- | -------- | ------------------------------------------------ |
| `serviceId`    | Yes      | Stable identifier for the paid capability.       |
| `agentCardUrl` | Yes      | URL of the seller's Agent Card.                  |
| `capability`   | Yes      | Capability id and compatible input/output modes. |
| `pricing`      | Yes      | Pricing model, currency, and amount.             |
| `settlement`   | Yes      | Accepted settlement methods and proof format.    |
| `receipts`     | Yes      | URL template for receipt/status lookup.          |

The `v1/samples/commerce-descriptor.json` fixture shows one ACP-style
descriptor. Other descriptor schemas can be used if both buyer and seller agree
on the contract.

## 3. Payment Proof Metadata

After settlement or authorization happens out of band, the buyer attaches a
payment proof to the A2A message metadata. The metadata key for this extension
is:

`github.com/a2aproject/a2a-samples/extensions/commerce-profile/v1/paymentProof`

The value SHOULD include:

| Field              | Required | Description                                 |
| ------------------ | -------- | ------------------------------------------- |
| `serviceId`        | Yes      | Service identifier from the descriptor.     |
| `settlementMethod` | Yes      | Settlement method used by the buyer.        |
| `proofType`        | Yes      | Proof type, for example `x402`.             |
| `proof`            | Yes      | Provider-specific proof token or reference. |
| `amount`           | Yes      | Amount authorized or paid.                  |
| `currency`         | Yes      | Settlement currency or unit.                |

Sellers MUST validate the payment proof before executing paid work. Buyers and
sellers SHOULD bind the proof to the requested `serviceId`, amount, and
request identity to prevent proof replay.

## 4. Execution Flow

1. Buyer fetches or discovers a seller Agent Card.
2. Buyer reads the Commerce Profile extension params.
3. Buyer fetches the descriptor URL and evaluates terms.
4. Buyer completes settlement or authorization out of band.
5. Buyer sends a normal A2A `message/send` request.
6. Buyer includes payment proof in message metadata.
7. Seller validates proof and executes the paid capability.
8. Seller returns or exposes a receipt identifier.
9. Buyer queries the receipt URL for reconciliation.

## 5. Receipts

A receipt SHOULD let both parties reconcile task execution with settlement.
Receipts SHOULD include:

- `receiptId`
- `serviceId`
- `taskId` or `contextId`
- final task status
- amount and currency
- settlement method and proof reference
- timestamps for authorization and completion

Receipts SHOULD NOT expose raw payment credentials, private keys, card details,
or reusable bearer tokens.

## 6. Security Considerations

Commerce descriptors, Agent Cards, messages, and receipts can all be supplied by
remote agents. Implementations MUST validate and sanitize all fields before
using them in prompts, logs, billing systems, or settlement systems.

Payment proof SHOULD be short lived or nonce-bound. Sellers SHOULD reject proofs
that do not match the descriptor terms, the requested capability, or the
expected amount. Buyers SHOULD keep local receipt records so they can detect
missing or inconsistent seller receipts.
