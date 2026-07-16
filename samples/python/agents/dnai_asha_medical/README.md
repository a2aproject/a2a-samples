# DNAi Asha — Medical Intelligence Agent

A hosted medical AI agent accessible via the A2A protocol. Asha provides
evidence-grounded clinical Q&A backed by 87M+ medical knowledge vectors
(PubMed, StatPearls, FDA drug labels, clinical guidelines).

**This is a hosted agent** — no local server required. Connect to the live
endpoint at `https://api.askasha.org/a2a/v1`.

Built by [DNAi Systems](https://dnai.systems) (physician-founded).

## Agent Card

```
https://api.askasha.org/.well-known/agent-card.json?agent_id=asha
```

## Skills

| Skill ID | Description |
|----------|-------------|
| `medical-qa` | Evidence-based medical Q&A |
| `drug-interaction-check` | Drug-drug interaction safety check |
| `clinical-guidelines` | Clinical guideline lookup (AHA, ADA, USPSTF) |
| `evidence-synthesis` | Multi-source literature synthesis |

## Getting Started

1. Get a free API key:

   ```bash
   curl -X POST https://api.askasha.org/api/a2a/signup \
     -H "Content-Type: application/json" \
     -d '{"email":"you@example.com","name":"Your Name","tier":"free"}'
   ```

2. Run the test client:

   ```bash
   ASHA_API_KEY=your_key uv run test_client.py
   ```

## Features

- **87M+ medical knowledge vectors** across 11 curated collections
- **Provenance in every response** — source collections, evidence count, contract hash
- **Falsification endpoint** — `/api/feng/falsify` for Popperian claim verification
- **Temporal queries** — "what did the system know at time T?"
- **Fiduciary contract** — cryptographically bound scope on every response

## More Information

- [Full documentation](https://github.com/EndlessRay/asha-a2a)
- [DNAi agent fleet](https://api.askasha.org/.well-known/agent-card.json) (11 agents)
- [askasha.org](https://askasha.org) (consumer app)
