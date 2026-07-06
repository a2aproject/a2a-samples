# Trace Trust Extension

This directory contains the specification and a Python sample implementation for the **Trace Trust Extension v1** for the Agent2Agent (A2A) protocol.

## Purpose

The A2A Protocol explicitly warns developers that incoming agent interactions are inherently untrusted and can lead to Sybil attacks or Prompt Injections if left unverified. The Trace Trust extension solves this by introducing a **global reputation verification layer** for A2A communication. 

It allows receiving agents (servers) to automatically evaluate the calling agent's global identity score using the TRACE API before accepting tasks, enabling:

* **Sybil Resistance:** Automatically drop requests from known malicious networks or newly spawned untrusted bots.
* **Safe Context Injection:** Only trust AgentCard data (like skills and intents) from agents with a verified positive reputation.
* **Granular Access Control:** Require high reputation scores for sensitive operations (e.g. executing financial transactions) while allowing lower scores for read-only queries.

## Specification

The full technical details, including data models, required fields, and security considerations, are documented here:

➡️ **[Full Specification (v1)](./v1/spec.md)**

## Sample Implementation

A runnable example demonstrating the implementation of the `TraceTrustExtension` middleware utility functions for integration with the A2A SDK is provided in the `samples` directory.

➡️ **[Python Sample Usage Guide](./v1/samples/python/README.md)**
