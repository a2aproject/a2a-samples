# A2A Protocol Extension: VAID (v1)

- **URI:** `https://github.com/solara-associates/vaid/blob/main/docs/a2a/v1/extension.md`
- **Type:** Profile Extension
- **Version:** 1 (draft)
- **Status:** draft, tracked against [a2aproject/A2A#2028](https://github.com/a2aproject/A2A/issues/2028)

## Where this fits

[a2aproject/A2A#2028](https://github.com/a2aproject/A2A/issues/2028) proposes
`actorChain`: a caller-supplied, append-only record of who acted for whom. The
thread converged on `actorChain` being attribution only, derived from a
validated credential, and never authority-bearing by itself, and on a per-hop
`proof_ref` (or `credentialRef`) as the slot where a receiver can plug in
something resolvable to check that credential's claim.

This extension is one concrete filler for that slot: a VAID is a signed,
attenuated, revocable delegation document. A hop that wants to back its
`actorChain` entry with a checkable proof sets `proof_ref` to the VAID's
`vaid_id` and carries the VAID itself under this extension's metadata key. A
receiver that understands both extensions resolves the reference locally,
against the VAID on the same message. A receiver that understands only
`actorChain` sees an opaque reference, which the #2028 thread already
establishes must never be read as a denial.

Carrying a VAID under this extension does not require `actorChain` to be
present, and this extension does not compete with it: `actorChain` stays the
audit record, VAID is one way to make a hop's claim in it resolvable.

## The specification

The normative spec (AgentCard declaration, activation, metadata shape,
verification order, and error mapping) lives in the VAID project itself
rather than being duplicated here, so there is one place to update it:

➡️ **[docs/a2a/v1/extension.md](https://github.com/solara-associates/vaid/blob/main/docs/a2a/v1/extension.md)**

Conformance vectors for the verification rules are at
[docs/a2a/v1/vectors](https://github.com/solara-associates/vaid/tree/main/docs/a2a/v1/vectors).

## Sample Implementation

A minimal Python sample showing an agent attaching a VAID to an A2A message
and a receiver verifying it with `vaid-a2a` is in the `samples` directory:

➡️ **[Python sample](./samples/python/)**
