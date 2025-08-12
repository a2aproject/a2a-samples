# Message/Artifact Timestamp Extension

## Overview

This extension defines how to add timestamp fields to `Message` and `Artifact`
objects.

## Extension URI

The URI of this extension is `https://github.com/a2aproject/a2a-samples/samples/extensions/timestamp/v1`.

This is the only URI accepted for this extension.

## Timestamp Format

All timestamps MUST be adhere to
[RFC 3339](https://datatracker.ietf.org/doc/html/rfc3339) and be specified in
the UTC time zone.

All timestamps MUST have at least second level precision. The maximum precision
for a timestamp is nanoseconds.

## Message/Artifact Metadata Field

Timestamps MUST be stored in the metadata for a Message or Artifact, under a
field with the key `github.com/a2aproject/a2a-samples/samples/extensions/timestamp/v1/timestamp`.

The value MUST be a string adhering to the [Timestamp format](#timestamp-format).

## Timestamp Generation

Timestamps added to a Message or Artifact MUST represent the time when the
object was created.

## Extension Activation

Clients indicate their desire to receive timestamps on messages by specifying
the [Extension URI](#extension-uri) via the transport-defined extension
activation mechanism. For JSON-RPC and HTTP transports, this is indicated via
the `X-A2A-Extensions` HTTP header. For gRPC, this is indicated via the
`X-A2A-Extensions` metadata value.
