# A2A Protocol Extension: Fidacy Trust-Verdict (v1)

- **URI:** `https://fidacy.com/a2a/extensions/trust-verdict/v1`
- **Type:** Profile Extension / Data-Only Extension
- **Version:** 1.0.0
- **Status:** Third-party (neutral). Not an official A2A extension; declarable and opt-in.

## Abstract

This extension lets an A2A agent carry a **trust verdict**, a signed `approve` / `review` / `deny`
decision about whether an agent action (typically a payment) should be trusted. The verdict is a
compact **EdDSA JWS** that any party verifies independently against a public JWKS, so it requires no
trust in the issuer. It is the complement to **x402** (settlement) and **AP2** (authorization): those
move and authorize money; this one carries the neutral risk decision the AP2 `risk_data` slot was
left open for.

Fidacy is the reference issuer; the format is verifiable by anyone with the open-source verifier.

## 1. Agent Card declaration

An agent advertises support in its Agent Card under `capabilities.extensions[]`:

```json
{
  "uri": "https://fidacy.com/a2a/extensions/trust-verdict/v1",
  "description": "Carries a Fidacy trust verdict (approve/review/deny), signed and independently verifiable.",
  "required": false,
  "params": {
    "issuer": "did:web:fidacy.com",
    "jwks_uri": "https://api.fidacy.com/.well-known/jwks.json",
    "trust_list_uri": "https://api.fidacy.com/.well-known/fidacy-trust-list.json",
    "verify_package": "@fidacy/verify"
  }
}
```

## 2. Where the verdict rides

The extension does not invent a new container. The verdict travels in existing fields:

- **AP2 flows (preferred):** inside the Cart/Payment Mandate's `risk_data` field as
  `{ "fidacy": { "decision", "score", "vc_jws", "signing_key_id", "payload" } }`.
- **Plain A2A flows:** in `Task.metadata` as `{ "fidacy_assessment": { … } }`, where the signed JWS
  is at `fidacy_assessment.risk_payload.jws`. The decision also maps to an official A2A Task state:

  | `decision` | recommended Task state    |
  | ---------- | ------------------------- |
  | `approve`  | `TASK_STATE_WORKING`      |
  | `review`   | `TASK_STATE_AUTH_REQUIRED`|
  | `deny`     | `TASK_STATE_REJECTED`     |

## 3. The signed verdict (source of truth)

The JWS (`vc_jws` / `risk_payload.jws`) is a compact **EdDSA** JWS, `typ: application/vc+jws`, whose
verified claims are the verdict:

| Claim           | Meaning                                                  |
| --------------- | -------------------------------------------------------- |
| `issuer`        | `did:web:fidacy.com#<kid>` (kid = JWKS key id)           |
| `subject`       | the agent/mandate assessed                               |
| `decision`      | `approve` \| `review` \| `deny`                          |
| `score`         | 0-100                                                    |
| `model_version` | scoring model id                                         |
| `assessed_at`   | ISO 8601                                                 |
| `signals`       | opaque advisory signals (not normative)                 |

## 4. Verification (normative)

The convenience fields (`decision`, `score`, …) are **untrusted hints** until the JWS is verified. A
recipient **MUST**:

1. Read the compact JWS from the container.
2. Fetch the public JWKS (`jwks_uri`), or confirm the active key via `trust_list_uri`.
3. Verify the **EdDSA** signature (e.g. `@fidacy/verify`, or any JOSE library pinned to `EdDSA`).
   `alg: none` and non-EdDSA algorithms **MUST** be rejected.
4. If valid, act on the claims; if invalid or expired, discard the verdict.

No trust in the issuer is required. The cryptography is checked directly.

## 5. Versioning

Breaking changes use a new URI (`…/trust-verdict/v2`). Agents that don't recognize the extension
ignore the `risk_data` / `Task.metadata` block and proceed with the base flow (backward compatible).

## References

- Canonical spec + schema: <https://fidacy.com/a2a/extensions/trust-verdict/v1> · [fidacy-open/spec](https://github.com/fidacy/fidacy-open/tree/main/spec)
- Open-source verifier: [`@fidacy/verify`](https://www.npmjs.com/package/@fidacy/verify)
- Public JWKS: <https://api.fidacy.com/.well-known/jwks.json>
