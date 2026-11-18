# Edge-Cloud Capability Contract Extension

This experimental sample specifies machine-readable placement, data residency,
SLO, side-effect, idempotency, attestation, and result-verification constraints
for A2A tasks spanning edge and cloud execution environments.

The extension is optional and uses existing A2A extension negotiation and
metadata. It does not replace A2A authentication, authorization, Agent Card
signatures, or deployment policy.

- [Version 1 specification](v1/spec.md)
- [Capability Contract schema](v1/capability-contract.schema.json)
- [Execution Requirements schema](v1/execution-requirements.schema.json)
- [Execution Receipt schema](v1/execution-receipt.schema.json)
- [Dependency-free reference validator](v1/contract.py)

The corresponding extension proposal is
[a2aproject/A2A#2076](https://github.com/a2aproject/A2A/issues/2076).
