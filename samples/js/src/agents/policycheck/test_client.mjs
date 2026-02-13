#!/usr/bin/env node
/**
 * PolicyCheck A2A Test Client
 *
 * Demonstrates interacting with a live hosted A2A service agent.
 * No dependencies required — uses native fetch.
 *
 * Usage: node test_client.mjs
 */

const A2A_ENDPOINT = "https://legaleasy.tools/api/a2a";
const AGENT_CARD_URL = "https://legaleasy.tools/.well-known/agent.json";

let rpcId = 0;

async function sendA2ARequest(message) {
  const body = {
    jsonrpc: "2.0",
    id: ++rpcId,
    method: "message/send",
    params: { message },
  };

  const res = await fetch(A2A_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

function printResult(label, response) {
  console.log(`\n${"=".repeat(60)}`);
  console.log(label);
  console.log("=".repeat(60));

  if (response.error) {
    console.log("ERROR:", response.error.message);
    return;
  }

  const task = response.result;
  console.log(`Task ID:  ${task.id}`);
  console.log(`Status:   ${task.status.state}`);

  // Print human-readable summary from status message
  const statusText = task.status?.message?.parts?.find((p) => p.kind === "text");
  if (statusText) {
    console.log(`\nSummary:\n${statusText.text}`);
  }

  // Print structured data from artifacts
  const dataArtifact = task.artifacts?.[0]?.parts?.find((p) => p.kind === "data");
  if (dataArtifact) {
    const d = dataArtifact.data;
    console.log(`\nStructured Data:`);
    console.log(`  Risk Level:            ${d.riskLevel}`);
    console.log(`  Buyer Protection Score: ${d.buyerProtectionScore}/100`);
    console.log(`  Recommendation:        ${d.recommendation}`);
    if (d.policiesFound) {
      console.log(`  Policies Found:        ${d.policiesFound.join(", ")}`);
    }
  }
}

async function main() {
  console.log("PolicyCheck A2A Test Client");
  console.log("Endpoint:", A2A_ENDPOINT);

  // ── Test 1: Discover agent card ──────────────────────────────────────────
  console.log(`\n${"=".repeat(60)}`);
  console.log("Test 1: Agent Card Discovery");
  console.log("=".repeat(60));

  const cardRes = await fetch(AGENT_CARD_URL);
  if (!cardRes.ok) {
    console.log(`ERROR: Could not fetch agent card (HTTP ${cardRes.status})`);
  } else {
    const card = await cardRes.json();
    console.log(`Name:         ${card.name}`);
    console.log(`Description:  ${card.description}`);
    console.log(`URL:          ${card.url}`);
    console.log(`Skills:       ${card.skills?.map((s) => s.id).join(", ")}`);
    console.log(`Version:      ${card.version}`);
  }

  // ── Test 2: Natural language analysis ────────────────────────────────────
  const nlResponse = await sendA2ARequest({
    role: "user",
    parts: [
      { kind: "text", text: "Quick check on https://www.amazon.com" },
    ],
  });
  printResult("Test 2: Natural Language Request (Amazon quick check)", nlResponse);

  // ── Test 3: Structured quick risk check ──────────────────────────────────
  const structuredResponse = await sendA2ARequest({
    role: "user",
    parts: [
      {
        kind: "data",
        data: { seller_url: "https://www.amazon.com", skill: "quick-risk-check" },
        mimeType: "application/json",
      },
    ],
  });
  printResult("Test 3: Structured Data Request (quick-risk-check)", structuredResponse);

  // ── Test 4: Raw policy text with known risks ─────────────────────────────
  const riskyText =
    "All sales are final. No refunds. By using this service you agree to " +
    "binding arbitration and waive your right to class action lawsuits. " +
    "Our liability shall not exceed $50. Your account may be terminated " +
    "at any time without notice. This subscription will auto-renew annually.";

  const textResponse = await sendA2ARequest({
    role: "user",
    parts: [{ kind: "text", text: riskyText }],
  });
  printResult("Test 4: Raw Policy Text (risky terms)", textResponse);

  console.log(`\n${"=".repeat(60)}`);
  console.log("All tests complete.");
  console.log("=".repeat(60));
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
