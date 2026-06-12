# Commerce Profile Extension

This directory contains an optional commerce profile for the Agent2Agent
(A2A) protocol. The profile demonstrates how a paid capability can advertise
commerce terms without changing A2A message transport.

## Purpose

The Commerce Profile extension shows how an A2A agent can expose:

- A stable Agent Card extension declaration.
- A descriptor URL for current pricing and settlement terms.
- A payment proof carried in A2A message metadata.
- A receipt URL for execution and settlement status.

The sample is intentionally rail-neutral. Payment can happen through x402,
stablecoin transfer, off-session card billing, invoice, prepaid credits, or
another provider-specific mechanism.

## Specification

The extension specification is documented here:

[Commerce Profile v1 specification](./v1/spec.md)

## Sample Fixtures

The `v1/samples` directory contains a minimal JSON flow:

- `agent-card.json`: seller Agent Card with the extension declaration.
- `commerce-descriptor.json`: ACP-style terms for one paid capability.
- `task-request.json`: A2A `message/send` request with mock payment proof.
- `receipt.json`: example receipt/status response after execution.
