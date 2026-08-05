# Settlement Extension

This directory contains the specification for the Settlement Extension: an
escrow-based payment mechanism for A2A agents. The extension shows:

- How agents declare pricing and settlement support in their AgentCard
- How escrow context travels through existing `Message` metadata fields
- How settlement actions map onto A2A `TaskState` transitions without any
  new task states
- How an external settlement exchange is defined as an interface, so any
  conforming implementation can serve as the settlement rail

The v1 directory contains the specification document. A library
implementation in Python is present in
`samples/python/extensions/settlement`, following the same structure as the
timestamp extension.
