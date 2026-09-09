import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const extensionRoot = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    ".."
);
const extensionUri =
    "https://github.com/a2aproject/a2a-samples/extensions/commerce-profile/v1";
const paymentProofKey = `${extensionUri}/paymentProof`;

async function fixture(name) {
    const source = await readFile(
        path.join(extensionRoot, "v1", "samples", name),
        "utf8"
    );
    return JSON.parse(source);
}

test("commerce fixtures use A2A 1.0 and preserve exact commerce bindings", async () => {
    const [card, descriptor, request, receipt] = await Promise.all([
        fixture("agent-card.json"),
        fixture("commerce-descriptor.json"),
        fixture("task-request.json"),
        fixture("receipt.json"),
    ]);

    assert.equal(Object.hasOwn(card, "url"), false);
    assert.deepEqual(card.supportedInterfaces, [
        {
            url: "https://seller.example.com/a2a",
            protocolBinding: "JSONRPC",
            protocolVersion: "1.0",
        },
    ]);
    const extension = card.capabilities.extensions.find(
        (candidate) => candidate.uri === extensionUri
    );
    assert.ok(extension);
    assert.equal(extension.required, false);
    assert.equal(extension.params.descriptorUrl.startsWith("https://"), true);
    assert.equal(
        extension.params.receiptUrlTemplate.startsWith("https://"),
        true
    );

    assert.equal(request.method, "SendMessage");
    const message = request.params.message;
    assert.equal(message.role, "ROLE_USER");
    assert.deepEqual(message.extensions, [extensionUri]);
    assert.equal(message.parts.length, 1);
    assert.deepEqual(Object.keys(message.parts[0]), ["text"]);

    const proof = message.metadata[paymentProofKey];
    assert.ok(proof);
    assert.equal(proof.serviceId, descriptor.serviceId);
    assert.equal(proof.termsId, descriptor.termsId);
    assert.equal(proof.requestId, request.id);
    assert.equal(proof.messageId, message.messageId);
    assert.equal(proof.amount, descriptor.pricing.unitAmount);
    assert.equal(proof.currency, descriptor.pricing.currency);
    assert.ok(
        descriptor.paymentProof.acceptedProofTypes.includes(proof.proofType)
    );
    assert.ok(
        descriptor.settlement.some(
            (method) =>
                method.method === proof.settlementMethod &&
                method.proofFormat === proof.proofType
        )
    );
    assert.ok(
        Date.parse(descriptor.issuedAt) < Date.parse(descriptor.validUntil)
    );

    assert.equal(receipt.receiptClass, "simulation");
    assert.equal(receipt.executionStatus, "completed");
    assert.equal(receipt.serviceId, proof.serviceId);
    assert.equal(receipt.termsId, proof.termsId);
    assert.equal(receipt.requestId, proof.requestId);
    assert.equal(receipt.a2a.messageId, proof.messageId);
    assert.equal(receipt.amount, proof.amount);
    assert.equal(receipt.currency, proof.currency);
    assert.equal(receipt.settlement.method, proof.settlementMethod);
    assert.equal(receipt.settlement.status, "simulated");
    assert.equal(receipt.settlement.confirmed, false);
    assert.notEqual(receipt.settlement.proofReference, proof.proof);
    assert.equal(
        receipt.settlement.proofReference,
        `sha256:${createHash("sha256").update(proof.proof).digest("hex")}`
    );
    assert.equal(receipt.usage.inputCharacters, message.parts[0].text.length);
});
