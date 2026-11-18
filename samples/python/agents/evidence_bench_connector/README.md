# Evidence Bench Connector Agent

This sample is a small A2A-to-A2A connector for a separately deployed
[Evidence Bench](https://github.com/kstawiski/evidence-gated-scientific-agent)
service. It demonstrates how one A2A agent can delegate a task to an external
scientific agent while retaining a local A2A task lifecycle.

The connector is **not** the Evidence Bench scientific engine. Qwen, Gemma,
Python/R execution, research tools, workspaces, validation, and provenance all
remain in the user-operated Evidence Bench deployment. Upstream tests use a fake
remote boundary and require no model, container, API key, or live service.

## A2A behavior

- The connector advertises JSON-RPC with stable A2A protocol version `1.0`.
- It accepts bounded text and raw file parts.
- `metadata.enable_code` defaults to `false`. When `metadata.mcp_servers` is
  omitted, `context7`, `brave-search`, and `chrome-devtools` are enabled to
  match Evidence Bench's default research profile. Send an explicit empty list
  to disable all MCP connections.
- It returns only bounded `report.md` and `run-summary.json` artifacts.
- It preserves the A2A context ID for follow-up work but creates a fresh remote
  message and never forwards the connector's local task ID.
- This initial sample does not proxy cancellation or remote input-required
  conversations. Use Evidence Bench directly when those features are required.

## Prerequisites

- Python 3.12 or later
- [`uv`](https://docs.astral.sh/uv/)
- A running Evidence Bench service with A2A enabled
- Its independent `A2A_TOKEN`

Do not use a public Evidence Bench deployment for confidential data. The sample
binds to loopback by default and has no authentication of its own, so every local
caller can use the configured remote credential. Brave and Context7 queries can
send generated search terms to external services; opt out with
`metadata.mcp_servers: []` for confidential tasks.

## Run the connector

From `samples/python/agents`:

```bash
export EVIDENCE_BENCH_URL=http://127.0.0.1:8080
read -rs EVIDENCE_BENCH_A2A_TOKEN
export EVIDENCE_BENCH_A2A_TOKEN
uv run --no-project --with-requirements evidence_bench_connector/requirements.txt \
  python -m evidence_bench_connector
```

The bearer token is read only from the environment. Do not place it in a command
argument, source file, Agent Card, or log.

In another terminal, use the repository's generic CLI host:

```bash
cd samples/python/hosts/cli
uv run . --agent http://127.0.0.1:9999
```

The connector intentionally exposes no remote deployment URL or credential in
its public Agent Card.

## Test and format

No live Evidence Bench instance is contacted by the test suite:

```bash
uv run --no-project --with-requirements evidence_bench_connector/requirements.txt \
  pytest -q evidence_bench_connector/test_agent.py
uv run ruff check --config ../../../.ruff.toml evidence_bench_connector
uv run ruff format --check --config ../../../.ruff.toml evidence_bench_connector
uv run --no-project --with-requirements evidence_bench_connector/requirements.txt \
  --with mypy mypy --config-file ../../../pyproject.toml evidence_bench_connector
uv run --no-project --with-requirements evidence_bench_connector/requirements.txt \
  --with pyright pyright evidence_bench_connector
```

## Security note

Agent Cards, messages, files, task states, and artifacts received from remote
agents are untrusted input. This sample validates the remote protocol and origin,
rejects URL file parts and unknown metadata, bounds forwarded inputs and returned
artifacts, and does not copy remote diagnostic text into local failures. It is a
teaching sample, not a production trust boundary.
