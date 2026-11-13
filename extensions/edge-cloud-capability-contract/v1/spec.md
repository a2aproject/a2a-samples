# A2A Edge-Cloud Capability Contract Extension (v1)

- **URI:** `https://github.com/a2aproject/a2a-samples/extensions/edge-cloud-capability-contract/v1`
- **Type:** Profile and data-only extension
- **Status:** Experimental sample

## Abstract

This extension defines machine-readable constraints for placing an A2A task
across edge and cloud execution sites. It covers execution location, data
classification and residency, latency and offline behavior, side effects,
idempotency, attestation, and result verification.

The extension uses existing A2A extension negotiation and metadata. It does not
add RPC methods or task states and does not replace authentication,
authorization, Agent Card signatures, or local policy.

## 1. Terminology

- **Contract:** A capability claim published by a callee in
  `AgentExtension.params`.
- **Requirements:** Caller constraints attached to an input `Message`.
- **Receipt:** A callee statement attached to a response `Message` or
  `Artifact`.
- **Execution site:** A declared edge or cloud location at which the capability
  can execute.

The key words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are to be
interpreted as described in RFC 2119.

## 2. Declaration and activation

An agent supporting this extension MUST add the following `AgentExtension` to
its Agent Card:

```json
{
  "uri": "https://github.com/a2aproject/a2a-samples/extensions/edge-cloud-capability-contract/v1",
  "description": "Placement and governance constraints for edge-cloud tasks",
  "required": false,
  "params": {
    "version": "1.0",
    "executionSites": [
      {
        "id": "device",
        "type": "edge",
        "region": "customer-premises",
        "p95LatencyMs": 20,
        "offlineCapable": true,
        "acceptedDataClassifications": ["public", "restricted"]
      },
      {
        "id": "cloud-cn-hangzhou",
        "type": "cloud",
        "region": "cn-hangzhou",
        "p95LatencyMs": 80,
        "offlineCapable": false,
        "acceptedDataClassifications": ["public"]
      }
    ],
    "sideEffects": {
      "kind": "external_write",
      "supportsIdempotencyKey": true
    },
    "attestationMethods": ["tpm-quote"],
    "verificationMethods": ["sha256-result"]
  }
}
```

The `params` object MUST conform to
[`capability-contract.schema.json`](capability-contract.schema.json).

Clients activate the extension using the transport-defined A2A extension
activation mechanism. For HTTP, the request includes:

```http
A2A-Extensions: https://github.com/a2aproject/a2a-samples/extensions/edge-cloud-capability-contract/v1
```

If the extension is not activated, both parties MUST preserve core A2A
behavior and MUST NOT assume these constraints were enforced.

## 3. Execution requirements

An activated request MUST place an `ExecutionRequirements` object in the input
`Message.metadata` map under the extension URI:

```json
{
  "https://github.com/a2aproject/a2a-samples/extensions/edge-cloud-capability-contract/v1": {
    "dataClassification": "restricted",
    "allowedSiteTypes": ["edge"],
    "allowedRegions": ["customer-premises"],
    "maxLatencyMs": 30,
    "networkMode": "offline",
    "idempotencyKey": "task-7b9c",
    "requiredAttestation": ["tpm-quote"],
    "requiredVerification": ["sha256-result"]
  }
}
```

The object MUST conform to
[`execution-requirements.schema.json`](execution-requirements.schema.json).

The callee MUST validate all requirements before causing a declared side
effect. If no execution site satisfies every requirement, the callee MUST
reject the request using an existing A2A error and MUST NOT silently relax the
requirements.

When `networkMode` is `offline`, the selected site MUST declare
`offlineCapable: true`.

For a capability whose `sideEffects.kind` is not `none`:

- the contract MUST declare `supportsIdempotencyKey: true`;
- the request MUST carry a non-empty `idempotencyKey`;
- repeated requests with the same authenticated caller, capability, and key
  MUST NOT cause the side effect more than once.

## 4. Execution receipt

After successful execution, the callee MUST attach an `ExecutionReceipt` to a
response `Message` or final `Artifact` metadata under the extension URI:

```json
{
  "https://github.com/a2aproject/a2a-samples/extensions/edge-cloud-capability-contract/v1": {
    "siteId": "device",
    "siteType": "edge",
    "region": "customer-premises",
    "contractDigest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "resultDigest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "verification": {
      "method": "sha256-result",
      "status": "passed"
    },
    "attestationReference": "urn:example:attestation:123"
  }
}
```

The receipt MUST conform to
[`execution-receipt.schema.json`](execution-receipt.schema.json). A receipt is
evidence for an external verifier; it is not proof merely because an agent
asserted it.

`contractDigest` MUST cover the canonical contract evaluated for the request.
`resultDigest` MUST cover the exact result representation defined by the
selected verification method. Verification methods MUST define their own
canonicalization rules.

## 5. Selection behavior

The included `contract.py` is a dependency-free reference matcher. It:

1. validates the contract version and required request constraints;
2. rejects unsupported attestation and verification methods;
3. fails closed for side-effecting calls without idempotency support;
4. filters sites by type, region, data classification, latency, and offline
   capability;
5. deterministically chooses the compatible site with the lowest declared p95
   latency.

Production implementations MAY use a different optimization policy, but MUST
enforce every caller requirement.

## 6. Security and privacy

- Contracts and receipts are claims. Clients MUST apply local authorization
  and data-governance policy and SHOULD verify Agent Card signatures when
  present.
- Attestation references MUST be verified by an independent trust policy
  before granting privilege.
- Raw credentials, user content, private topology, and sensitive device
  identifiers MUST NOT be placed in extension metadata.
- `idempotencyKey` SHOULD be an opaque random identifier. Receipts SHOULD
  include only a digest when correlating it.
- Servers MUST validate extension input as untrusted data and MUST apply the
  same authentication and authorization checks used by core A2A operations.
- A gateway MUST NOT infer that data may leave an allowed region merely
  because a remote agent advertises the capability.

## 7. Relationship to MCP

MCP tool annotations describe properties of tools available within an agent's
runtime and are hints rather than a cross-agent authorization mechanism. This
extension operates at the A2A task boundary. An orchestrator MAY translate
verified MCP tool properties into stricter A2A requirements, but MUST NOT treat
unverified tool annotations as attestation.

## 8. Versioning

Breaking changes require a new extension URI. Additive schema changes MAY be
introduced only when old implementations can safely ignore them; otherwise a
new URI is required.
