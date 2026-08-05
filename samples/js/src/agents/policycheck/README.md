# PolicyCheck — Live A2A Service Agent

A production A2A service agent for e-commerce policy analysis. PolicyCheck helps AI purchasing agents verify sellers before completing transactions on behalf of users.

## Architecture

```
┌────────────────────┐     JSON-RPC 2.0      ┌────────────────────┐
│                    │    POST /api/a2a       │                    │
│  Purchasing Agent  │ ──────────────────────▶│  PolicyCheck A2A   │
│  (A2A Client)      │                        │  Server            │
│                    │◀──────────────────────  │                    │
└────────────────────┘    Task + Artifacts     └────────┬───────────┘
                                                        │
                                                        ▼
                                               ┌────────────────────┐
                                               │  Policy Analysis   │
                                               │  Engine            │
                                               │                    │
                                               │  • Risk detection  │
                                               │  • Score (0-100)   │
                                               │  • Recommendations │
                                               └────────────────────┘
```

## Skills

| Skill ID | Name | Description |
|----------|------|-------------|
| `comprehensive-policy-analysis` | Comprehensive Policy Analysis | Full analysis of returns, shipping, warranty, and terms |
| `quick-risk-check` | Quick Risk Check | Auto-discovers and analyzes policies from a store URL |
| `returns-policy-analysis` | Returns Policy Analysis | Focused return/refund policy analysis |
| `shipping-policy-analysis` | Shipping Policy Analysis | Focused shipping policy analysis |
| `warranty-analysis` | Warranty Analysis | Focused warranty coverage analysis |
| `terms-analysis` | Terms & Conditions Analysis | Legal risk analysis (arbitration, liability, etc.) |

## Usage Examples

### Natural language request

```bash
curl -X POST https://legaleasy.tools/api/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Quick check on https://www.amazon.com"}]
      }
    }
  }'
```

### Structured data request

```bash
curl -X POST https://legaleasy.tools/api/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{
          "kind": "data",
          "data": {"seller_url": "https://www.amazon.com", "skill": "quick-risk-check"},
          "mimeType": "application/json"
        }]
      }
    }
  }'
```

### Raw policy text analysis

```bash
curl -X POST https://legaleasy.tools/api/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{
          "kind": "text",
          "text": "All sales are final. No refunds. By using this service you agree to binding arbitration and waive your right to class action lawsuits. Liability shall not exceed $100."
        }]
      }
    }
  }'
```

## Response Format

The A2A response follows standard JSON-RPC 2.0 with task status and artifacts:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "id": "task_1234567890_abc1234",
    "status": {
      "state": "completed",
      "message": {
        "role": "agent",
        "parts": [{"kind": "text", "text": "Risk Level: HIGH\nBuyer Protection Score: 50/100\n..."}]
      }
    },
    "artifacts": [{
      "artifactId": "artifact_1234567890_def5678",
      "name": "policy_analysis",
      "parts": [
        {
          "kind": "data",
          "data": {
            "riskLevel": "high",
            "buyerProtectionScore": 50,
            "recommendation": "review_carefully",
            "keyFindings": [
              "Binding arbitration required",
              "Class action lawsuits waived",
              "No refunds - all sales are final",
              "Liability capped at $100"
            ],
            "risks": {
              "arbitration": true,
              "classActionWaiver": true,
              "noRefunds": true,
              "liabilityCap": 100
            }
          },
          "mimeType": "application/json"
        },
        {
          "kind": "text",
          "text": "Risk Level: HIGH\nBuyer Protection Score: 50/100\nRecommendation: review_carefully"
        }
      ]
    }]
  }
}
```

## Integration Example

Using PolicyCheck in a purchasing agent workflow:

```javascript
async function checkSellerBeforePurchase(sellerUrl) {
  const response = await fetch("https://legaleasy.tools/api/a2a", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method: "message/send",
      params: {
        message: {
          role: "user",
          parts: [{
            kind: "data",
            data: { seller_url: sellerUrl, skill: "quick-risk-check" },
            mimeType: "application/json"
          }]
        }
      }
    })
  });

  const { result } = await response.json();
  const analysis = result.artifacts[0].parts.find(p => p.kind === "data").data;

  if (analysis.buyerProtectionScore < 60) {
    console.log(`Warning: ${analysis.riskLevel} risk - ${analysis.recommendation}`);
    return false; // Do not proceed with purchase
  }
  return true; // Safe to proceed
}
```

## Multi-Protocol Support

PolicyCheck is available via multiple protocols:

| Protocol | Endpoint | Use Case |
|----------|----------|----------|
| **A2A** | `https://legaleasy.tools/api/a2a` | Agent-to-agent communication |
| **MCP** | `npx -y policycheck-mcp` | Claude Desktop, Claude Code, Cursor |
| **x402** | `POST https://legaleasy.tools/api/x402/analyze` | Paid analysis via crypto micropayments |

## Links

- **Agent Card:** https://legaleasy.tools/.well-known/agent.json
- **A2A Endpoint:** https://legaleasy.tools/api/a2a
- **MCP Package:** https://www.npmjs.com/package/policycheck-mcp
- **Website:** https://legaleasy.tools

## Running the Test Client

```bash
node test_client.mjs
```

No dependencies required — uses native `fetch`.
