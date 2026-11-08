# AGENTS.md — ACP fleet

## Project overview

A fleet of a2a-go servers that runs ACP agents with the `a2aacp` executor in cluster mode. Conversations are split into virtual shards that move between servers. See `README.md` for the design.

## Layout

```text
acp-fleet/
├── main.go          # serve, fakeacp, mcp and status subcommands; config from the environment
├── internal/
│   ├── agents/      # a2aacp wiring: Agent, Turn, Session, SessionStore; stops a shard's agents before it moves
│   ├── fakeacp/     # scripted ACP agent over stdio
│   ├── mcpscratch/  # MCP server with file tools in a scratch directory
│   ├── nodes/       # heartbeats in the NODES bucket
│   ├── router/      # push queue writer; forwards payloads to shard owners over NATS
│   ├── server/      # wiring and drain
│   ├── shards/      # shard assignment, records, snapshots, claim and release
│   ├── status/      # the status subcommand
│   └── tasks/       # fails abandoned and orphaned tasks
├── itest/           # in-process fleets against NATS and MySQL
└── infra/           # docker-compose.yaml, nginx.conf
```

The task store and event queues come from `integrations/mysql` and `integrations/nats`, which `go.mod` replaces with the local directories. Docker builds from `samples/go`.

## Rules

- `main.go` is the only file in package `main`. One concern per package under `internal/`.
- A shard's record is its manifest and its fencing token. Change it only with a compare-and-swap through `shards.Shard`, and treat a failed swap as a lost shard.
- Run `go test ./...` before sending changes. The integration tests start NATS and MySQL with the compose file of `integrations/mysql` if they aren't running, and the servers run the test binary as their agent.
- Log with `github.com/a2aproject/a2a-go/v2/log`.
