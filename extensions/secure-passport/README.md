# Secure Passport Extension

This directory contains the specification and a Python sample implementation for the **Secure Passport Extension v1** for the Agent2Agent (A2A) protocol.

## Purpose

The Secure Passport extension introduces a **trusted, contextual layer** for A2A communication. It allows a calling agent to securely and voluntarily share a structured subset of its current contextual state with the callee agent. This is designed to transform anonymous, transactional calls into collaborative partnerships, enabling:

* **Immediate Personalization:** Specialist agents can use context (like loyalty tier or preferred currency) immediately.
* **Reduced Overhead:** Eliminates the need for multi-turn conversations to establish context.
* **Enhanced Trust:** Includes a **`signature`** field for cryptographic verification of the data's origin and integrity.

## Specification

The full technical details, including data models, required fields, and security considerations, are documented here:

➡️ **[Full Specification (v1)](./v1/spec.md)**

## Sample Implementation

A runnable example demonstrating the implementation of the `CallerContext` data model and the utility functions for integration with the A2A SDK is provided in the `samples` directory.

➡️ **[Python Sample Usage Guide](./v1/samples/python/README.md)**