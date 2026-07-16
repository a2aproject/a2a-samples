# Envoys RFC 9421 Message Signing Extension

This directory contains the specification for the **RFC 9421 Message Signing
Extension v1** for the Agent2Agent (A2A) protocol.

## Purpose

A2A's transport and session security (API keys, OAuth2, mTLS) authenticate the
*connection*, and AgentCard signing attests to an agent's *card* at rest. This
extension adds the missing piece: **per-message proof of origin** — a
cryptographic guarantee that an individual A2A request genuinely came from the
agent it claims to be from.

Agents that support this extension sign every A2A request with
[RFC 9421 HTTP Message Signatures](https://www.rfc-editor.org/rfc/rfc9421) over
an Ed25519 key. The signature's `keyid` is a resolvable URL that returns the
signing agent's public key, so a verifier can confirm the sender's identity with
no shared secret and no central broker — enabling allowlisting, auditing, and
authorization by **stable agent identity** rather than by an opaque token. The
signature is carried in the standard HTTP `Signature`, `Signature-Input`, and
`Content-Digest` headers and does not modify any core A2A data structure.

## Specification

➡️ **[Full Specification (v1)](./v1/spec.md)**

## Reference Implementations

The wire format is the
[Envoys signature specification](https://envoys.me/specs/signature/v1)
(RFC 9421 + Ed25519 + resolvable keyids), with Apache-2.0 implementations in:

- **Node:** [`@envoys/sdk`](https://www.npmjs.com/package/@envoys/sdk) (signing +
  verification) and [`@envoys/a2a`](https://www.npmjs.com/package/@envoys/a2a)
  (A2A adapter: signed JSON-RPC over RFC 9421)
- **Python:** [`envoys`](https://pypi.org/project/envoys/) (signing +
  verification) and [`envoys-mcp`](https://pypi.org/project/envoys-mcp/) (MCP
  transport integration)
