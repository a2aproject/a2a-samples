# Message Signing Extension v1

> [!IMPORTANT]
> This extension serves as an example for how extensions work in A2A. It is not intended for production usage.

## Overview

This extension describes how to add signatures to `Message` and `Artifact` objects in A2A. This
allows verifying that the message was authored by an A2A Agent.

## Extension URI

The URI of this extension is:
`https://github.com/a2aproject/a2a-samples/samples/extensions/signing/v1`

This is the only accepted URI for this extension.

## Extension Parameters

The `AgentExtension.params` field has the following schema:

```json
{
    "title": "Signing Extension Params",
    "description": "Parameters used for the signing extension in an AgentCard",
    "type": "object",
    "properties": {
        "jwk": {
            "type": "string",
            "description": "The public JSON Web Key (JWK) used for adding signatures to messages"
        }
    },
    "required": ["jwk"]
}
```

Every agent that supports signing must expose a JWK that verifiers can use to verify that the
message was authored by the agent.

> [!TIP]
> For a real signing extension, this field would be more flexible: specifying a set of keys, or a URI to a key set, for example.

## Message and Artifact Signature Field

With this extension, both `Message` and `Artifact` objects can have signatures.

Signatures are attached to `Message` and `Artifact` objects via the `metadata` field. Signatures
MUST use the following key for the signature object in metadata:

`github.com/a2aproject/a2a-samples/samples/extensions/signing/v1/signature`

The value for the signature MUST be an object with the following two fields:

- `signature`: The value MUST be a JSON Web Signature (JWS) in compact serialization form with detached payload.
- `agent_url`: The value MUST be a URL that resolves to an AgentCard.

The full JSON schema for the metadata field is:
```json
{
    "type": "object",
    "description": "A verifiable signature for a message or artifact",
    "properties": [
        "agent_url": {
            "type": "string",
            "description": "The URL of the AgentCard for the agent that added the signature"
        },
        "jws": {
            "type": "string",
            "description": "A JWS in compact form with detached payload containing the signature for the message"
        }
    ],
    "required": ["agent_url", "jws"]
}
```

An example message with an attached signature is shown below:

```json
{
    "role": "agent",
    "messageId": "3f36680c-7f37-4a5f-945e-d78981fafd36",
    "taskId": "3f36680c-7f37-4a5f-945e-d78981fafd36",
    "contextId": "c295ea44-7543-4f78-b524-7a38915ad6e4",
    "parts": [
        {
            "kind": "text",
            "text": "Okay, I've found a flight for you. Confirmation XYZ123. Details are in the artifact."
        }
    ],
    "metadata": {
        "github.com/a2aproject/a2a-samples/samples/extensions/signing/v1/signature": {
            "agent_url": "https://agents.example.com/travel/v1/agent-card.json",
            "jws": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpPU0UifQ..YYseIUE4F_2NbnRecbxTN1Xcc1fjgWi775vhtxQcVpcq6A0N9Z3b6XIpMdTMo2SXJ66Ne3h14fa2JHp3n4hToA"
        }
    }
}
```

## Signing and Verification Process

Signatures are generated using the JSON representation of the `Message` or `Artifact`. The process is
as follows:

To sign a Message or Artifact:

1. Retrieve the signing key that is exposed via the AgentCard.
1. Serialize the Message or Artifact to JSON, omitting the [signature field](#message-and-artifact-signature-field), if present.
1. Canonicalize the JSON message according to JSON Canonicalization Scheme (JCS).
1. URL-safe Base64-encode the resulting canonicalized JSON
1. Generate a JWS protected header that encodes, at least, the `alg` used for signing.
    1. The signature algorithm MUST be based on asymmetric encryption, such as `ES256` or `EdDSA`.
1. Create the compact JWS using the signing key, protected header, and base64-encoded payload.
1. Detach the payload value from the resulting signature
1. Add the signature and canonical URL of the AgentCard in the [signature field](#message-and-artifact-signature-field).


To verify the signature on a Message or Artifact:

1. Extract the [signature field](#message-and-artifact-signature-field) from the Message or Artifact `metadata`.
1. Resolve the AgentCard referenced by the `agent_url` field.
1. Find the AgentExtension that uses the [Extension URI](#extension-uri).
    1. If this extension is not found, signature verification fails.
1. Parse and validate the JWK from the AgentExtension.
    1. If parsing or validating this JWK fails, signature verification fails.
1. Serialize the Message or Artifact to JSON, omitting the [signature field](#message-and-artifact-signature-field).
1. Canonicalize the JSON message according to JSON Canonicalization Scheme (JCS).
1. URL-safe Base64-encode the resulting canonicalized JSON
1. Construct the compact JWS value by inserting the base64-encoded payload into the payload position of the JWS `signature` field.
1. Verify the JWS using the resolved JWK for the AgentCard.

## Extension Activation Requirements

A client MAY request activation of the extension by including the [Extension URI](#extension-uri) in
the `X-A2A-Extensions` header sent in requests to the agent.

An agent that supports message signatures MUST NOT include signatures unless explicitly requested by
a client via extension activation.

A client that supports signing MAY include signatures on requests where the signing extension is activated.
A client may choose to request activation of the signing extension, but not provide signed messages in
the request to the server.

An agent that receives a request with a signed message MUST verify that signature. If signature verification
fails, the agent MUST fail the request.