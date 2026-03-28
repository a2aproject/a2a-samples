# Settlement Extension

This directory contains the specification for the A2A Settlement Extension
(A2A-SE), which adds escrow-based token settlement to the A2A task lifecycle.

The extension enables agents to:

- Declare skill-level pricing in their Agent Cards
- Hold funds in escrow while work is in progress
- Release payment on task completion, refund on failure
- Resolve disputes when requester and provider disagree

A2A-SE is a **data + profile extension**: it adds structured settlement data to
Agent Cards and overlays settlement metadata onto the core request-response
messages via the `metadata` field. It does not add new RPC methods or task
states to the core protocol.

The v1 directory contains the specification document. A library implementation
in Python is present in `samples/python/extensions/settlement`. A live reference
exchange is available at <https://exchange.a2a-settlement.org/api/v1>.

## Resources

- [Full specification](https://github.com/a2a-settlement/a2a-settlement/blob/main/SPEC.md)
- Python SDK: `pip install a2a-settlement` ([source](https://github.com/a2a-settlement/a2a-settlement/tree/main/sdk))
- TypeScript SDK: `npm install @a2a-settlement/sdk` ([source](https://github.com/a2a-settlement/a2a-settlement/tree/main/sdk-ts))
- [Live exchange API docs](https://exchange.a2a-settlement.org/docs)
