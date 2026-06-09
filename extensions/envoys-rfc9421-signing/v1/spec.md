# A2A Protocol Extension: Envoys RFC 9421 Message Signing (v1)

## Abstract

This extension defines per-message cryptographic proof of origin for A2A
requests. An agent that supports this extension signs every A2A request with an
[RFC 9421 HTTP Message Signature](https://www.rfc-editor.org/rfc/rfc9421) over an
[Ed25519](https://www.rfc-editor.org/rfc/rfc8410) key. The signature's `keyid` is
a resolvable HTTPS URL that returns the signer's public key, allowing a verifier
to confirm *which* agent sent each request — with no shared secret and no central
registry. The normative wire format is the
[Envoys signature specification](https://envoys.me/specs/signature/v1).

This is a **profile** extension: it constrains how requests are authenticated at
the HTTP layer and does not add or modify any core A2A data structure.

## Motivation

A2A's transport and session security (`APIKey`, `HTTPAuth`, `OAuth2`, `mTLS`)
authenticate the connection, and AgentCard signing attests to an agent's card at
rest. Neither proves that an individual in-flight request originated from the
claimed agent. This extension fills that gap, enabling a receiver to allowlist,
audit, and authorize by stable agent identity rather than by an opaque bearer
token.

## Extension URI

The URI of this extension is
`https://github.com/a2aproject/a2a-samples/extensions/envoys-rfc9421-signing/v1`.

This is the only URI accepted for this extension.

## Agent Declaration

An agent that signs — or requires signed — A2A requests **MUST** declare support
in its `AgentCard` under the `extensions` field of the `AgentCapabilities`
object:

```json
{
  "name": "Signed Agent",
  "url": "https://agent.example/a2a",
  "capabilities": {
    "extensions": [
      {
        "uri": "https://github.com/a2aproject/a2a-samples/extensions/envoys-rfc9421-signing/v1",
        "required": false
      }
    ]
  }
}
```

When `required` is `true`, the agent **MUST** reject unsigned or invalid
requests.

## Signature Scheme

Requests are signed per [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421) with
the following profile (full normative detail in the
[Envoys signature specification](https://envoys.me/specs/signature/v1)):

- **Algorithm:** Ed25519 ([RFC 8410](https://www.rfc-editor.org/rfc/rfc8410)).
- **Covered components:** `"@method"`, `"@path"`, and `"content-digest"` are
  always covered. Senders **SHOULD** additionally cover `"@authority"` (the
  lowercased target host) when the target is known at signing time — this
  scopes the signature to one receiving service, so it cannot be relayed to a
  different host within the freshness window.
- **Signature parameters:** `keyid`, `created`, `nonce`, and an **OPTIONAL**
  `tag` (RFC 9421 §2.3) disambiguating signing purpose.
- **Body integrity:** a `Content-Digest` header
  ([RFC 9530](https://www.rfc-editor.org/rfc/rfc9530); SHA-256, or SHA-512 for
  bodies of 4096 bytes or more) is always signed.
- **keyid resolution:** `keyid` is an HTTPS URL that returns the signer's public
  key, as either an Envoys-native `{ address, public_key }` object or a W3C DID
  Document (`application/did+json`).

The signature is carried in the standard `Signature`, `Signature-Input`, and
`Content-Digest` HTTP headers. It applies to every A2A transport with HTTP
request/response semantics (JSON-RPC and HTTP+JSON/REST).

## Verification

A verifier that has activated this extension **MUST**, for each signed request:

1. Check that the covered components listed in `Signature-Input` include
   `"@method"` and `"@path"`, and — when the request has a body —
   `"content-digest"`. A signature omitting a required component **MUST** be
   rejected even if cryptographically valid: without this check, an attacker
   can substitute the body together with a matching `Content-Digest` header
   while the signature still verifies.
2. Verify the `Content-Digest` matches the received body.
3. Resolve the `keyid` URL to obtain the signer's Ed25519 public key.
4. Verify the RFC 9421 signature over the covered components. When
   `"@authority"` is covered, reconstruct its value from the verifier's own
   authority (configuration or the `Host` header) — never from a
   sender-controlled field.
5. Reject signatures whose `created` timestamp falls outside an acceptable
   freshness window (replay protection).

A successful verification establishes the sender's cryptographic identity (the
`keyid` / address). Authorization — deciding whether that identity may perform
the requested action — is a separate, application-defined step (for example, an
allowlist).

## Extension Activation

Clients activate this extension via the A2A extension activation mechanism — the
`A2A-Extensions` header for HTTP / JSON-RPC transports, and the equivalent
metadata for gRPC — as defined in the
[A2A specification](https://a2a-protocol.org/latest/specification/). Activation
is independent of the signature itself: an agent **MAY** sign requests whenever
it holds a key, and a verifier enforces signing for agents that declare this
extension as `required`.

## Reference Implementations

All reference implementations are Apache-2.0 licensed. The signing libraries
share one wire format and a common set of reference test vectors:

| Language | Package | Role |
| --- | --- | --- |
| Node   | [`@envoys/sdk`](https://www.npmjs.com/package/@envoys/sdk)   | signing + verification |
| Node   | [`@envoys/a2a`](https://www.npmjs.com/package/@envoys/a2a)   | A2A adapter (signed JSON-RPC over RFC 9421) |
| Python | [`envoys`](https://pypi.org/project/envoys/)                 | signing + verification |
| Python | [`envoys-mcp`](https://pypi.org/project/envoys-mcp/)         | MCP Streamable-HTTP integration |

## Security Considerations

- **Identity is not authorization.** A valid signature proves origin, not
  permission. Pair verification with an allowlist or policy.
- **Key-resolution trust.** The `keyid` URL **MUST** be fetched over HTTPS.
  Verifiers **SHOULD** pin the first-seen `(address, public_key)` pair and treat
  a changed key as a rotation event requiring re-validation.
- **Replay.** The `created` timestamp and `nonce` bound replay; verifiers
  **MUST** enforce a freshness window.
- **Cross-host relay.** A signature that does not cover `"@authority"` is valid
  for the same method and path on any host within the freshness window, and
  per-receiver replay caches cannot detect the relay. Covering `"@authority"`
  closes this; senders **SHOULD** do so whenever the target host is known.
- **Scope.** A signature attests to "this request body at this moment," not to a
  whole task or session.
