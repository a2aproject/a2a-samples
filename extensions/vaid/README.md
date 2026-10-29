# VAID Extension

This directory contains the specification and a minimal Python sample for the
**VAID A2A extension v1**.

## What it is, in plain words

When one agent delegates work to another, A2A's
[`actorChain`](https://github.com/a2aproject/A2A/issues/2028) proposal lets
each hop record who it acted for. That record is self-reported, so on its own
it proves nothing about whether the hop actually had the authority it claims,
since a fabricated chain narrows just as cleanly as a real one. The #2028 thread's
answer is a `proof_ref`: a reference a receiver can resolve to something
checkable.

A **VAID** is one concrete thing that reference can point to: a signed
document that says "this agent may do these things, until this time, because
this parent granted it", plus the Ed25519 signature that proves nobody
tampered with it. A receiver can check a VAID completely offline: verify the
signature against a key it already trusts, check it hasn't expired, check
that each step of its lineage only narrowed what came before, check the
specific thing being requested is actually in its scope, and check it hasn't
been revoked.

This extension says exactly how a VAID travels on an A2A `Message` and the
order a receiver checks it in. It does not replace `actorChain` or require
it: a hop can carry a VAID as the resolvable proof behind its `actorChain`
entry, or on its own.

## How to run

```sh
cd extensions/vaid/v1/samples/python
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python3 run.py
```

### Real output from the command above

```
VAID A2A extension: minimal accept/refuse demo
issuer trust domain: 'vaid.example', agent scope: [{'kind': 'prefix', 'value': 'data.orders.read'}]
  requested_action='data.orders.read' -> ACCEPTED (allowed: signature, expiry, chain integrity, attenuation, requested-action scope and revocation all checked clean)
  requested_action='data.orders.write' -> REFUSED (out_of_scope: requested action 'data.orders.write' is outside the leaf's scope_boundary)
```

The sample mints a VAID scoped to `data.orders.read`, attaches it to an A2A
message, and verifies it against two requested actions: one inside that
scope (accepted) and one outside it (refused). It installs `vaid-a2a` from
PyPI; it does not mint or verify anything through a network call.

## Specification

The extension's normative details (AgentCard declaration, activation,
metadata shape, verification order, error mapping) are in
[`v1/spec.md`](./v1/spec.md), which links to the canonical spec rather than
duplicating it.
