# Fidacy Trust-Verdict Extension

This directory contains the specification and a Python sample implementation for the **Fidacy
Trust-Verdict Extension v1** for the Agent2Agent (A2A) protocol.

## Purpose

The Trust-Verdict extension lets an A2A agent carry a **signed, independently verifiable trust
verdict** (`approve` / `review` / `deny`) about whether an agent action, typically a payment , 
should be trusted. It is the complement to **x402** (settlement) and **AP2** (authorization): it
fills the neutral risk decision the AP2 `risk_data` slot was reserved for.

* **Neutral & verifiable:** the verdict is a compact EdDSA JWS anyone verifies against a public JWKS, no trust in the issuer required.
* **No new container:** the verdict rides the existing AP2 `risk_data` field or A2A `Task.metadata`.
* **Declarable:** an agent advertises it in its Agent Card; clients opt in.

## Specification

➡️ **[Full Specification (v1)](./v1/spec.md)** · Canonical URI: <https://fidacy.com/a2a/extensions/trust-verdict/v1>

## Sample Implementation

A runnable Python example assesses a mandate over A2A and verifies the signed verdict against the
public JWKS.

➡️ **[Python Sample Usage Guide](./v1/samples/python/README.md)**

## Verifier

Open-source verifier (TypeScript/JS): [`@fidacy/verify`](https://www.npmjs.com/package/@fidacy/verify).
Python verification uses any EdDSA-capable JOSE library (the sample uses `PyJWT[crypto]`).
