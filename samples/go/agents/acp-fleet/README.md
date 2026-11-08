# ACP fleet

A fleet of a2a-go servers behind a load balancer that runs ACP coding agents in cluster mode. Each conversation keeps its agent, its pending questions and its memory when servers crash, drain or join.

Built with [a2a-go](https://github.com/a2aproject/a2a-go) and its [`a2aacp`](https://pkg.go.dev/github.com/a2aproject/a2a-go/v2/integrations/executor/a2aacp) executor.

## Overview

* Conversations are split into 64 virtual shards. Each shard is a directory with a SQLite session map, the agent homes and the scratch directories of its conversations.
* Servers own shards by rendezvous hashing. When a server joins or leaves, only its shards move.
* Any server takes any request and forwards it to the owner of the conversation's shard, so nginx needs no sticky sessions.
* Agent homes and the session map are saved to the NATS object store after every turn, so a crash loses no memory. Scratch directories move when a shard moves gracefully, and a crash loses them.
* Every agent gets a scratch MCP server with file tools in its working directory.
* A fake ACP agent runs the demo without model keys. Gemini CLI can replace it.

## Running

1. Start NATS, MySQL, three servers and nginx on `:8080`:

   ```console
   make up
   ```

2. Chat with the fleet using the [a2a CLI](https://github.com/a2aproject/a2a-cli) v0.4.0 or later:

   ```console
   make chat
   ```

The fake agent understands:

| Message | Reply |
| --- | --- |
| `save <note>` | Asks permission, then appends the note to `notes.txt` in its home |
| `scratch <text>` | Appends the text to `scratch.txt` in its scratch directory |
| `work <seconds>` | Reports a step every second until done or canceled |
| anything else | The turn number, where earlier turns ran, and what it remembers |

To use Gemini CLI, set `GEMINI_API_KEY` in your environment and run `make up-gemini`. Gemini CLI supports `session/load`, so it keeps its memory when its shard moves.

## Try it

Every reply starts with the server that runs the agent.

```console
> hi, I'm Yaro
server-2: turn 1, new session. You said: hi, I'm Yaro. MCP: scratch
> save milk
[status] input-required: Permission required: Append "milk" to notes.txt.
Reply with one of: once, reject.
> once
server-2: turn 2, saved. Notes: milk
> scratch v1
server-2: turn 3, scratch.txt: v1
```

nginx spread these requests over all three servers, and each one reached server-2. `make logs` shows the forwarding.

Crash the server that runs the agent, and continue:

```console
$ make kill S=server-2
> what do you remember?
server-3: turn 4, session loaded; turns 1-3 ran on server-2. Earlier you said: hi, I'm Yaro | save milk | scratch v1. Notes: milk. MCP: scratch. Scratch was lost when the conversation moved
```

server-3 took the shard over once server-2's heartbeat expired, restored the agent home saved after turn 3, and the agent loaded its session. A turn that was running on server-2 fails with a message that asks to send it again.

Add a server, or stop one gracefully:

```console
$ make join            # server-4 takes about a quarter of the shards
$ make drain S=server-3
$ make status
SERVER    INCARNATION  STATE  SHARDS  CONVERSATIONS
server-1  2d98dd9c     live   31      2
server-4  da9f7326     live   33      0
```

A draining server lets running turns finish, saves the scratch directories with its shards, and exits. Its conversations continue on other servers with their scratch directories.

## How it works

| What | Where it lives | Graceful move | Crash |
| --- | --- | --- | --- |
| Session map (`sessions.db`) | SQLite in the shard directory | moves with the shard | restored from the snapshot of the last turn |
| Agent home | `homes/<context>` in the shard directory | moves with the shard | restored from the snapshot of the last turn |
| Scratch | `scratch/<context>`, the agent's working directory | moves with the shard | lost, and the agent is told |
| Tasks | MySQL index and NATS events ([`integrations`](../../integrations)) | shared | shared |

* **Membership.** Each server rewrites its record in the `NODES` KV bucket every 2 seconds. A record expires 8 seconds after its last write, and every server sees the expiry. A server that can't write its record exits.
* **Shards.** The `SHARDS` bucket has a record per shard: the owner, an epoch, and the snapshots of its session map, homes and scratch directories in the `SHARD_DATA` object store. Every claim and save is a compare-and-swap on that record, so a server that lost a shard can't overwrite it.
* **Routing.** The work queue is `workqueue.NewPushQueue` with a router as its writer. The router finds the conversation's shard and runs the payload if this server owns it, or forwards it to the owner with NATS request/reply. While a shard moves, its payloads wait for the new owner, except answers and cancels for turns still running on the old one.
* **Agents.** The `a2aacp.Agent` restores a conversation's home and scratch directory on its first message, then starts the agent with `HOME` set to the home and the scratch directory as its working directory. `Config.Turn` saves the home after every turn, `Config.SessionStore` reads the shard's SQLite map, and `Config.Abandoned` stores the failure of a question nobody answered.
* **Takeover.** A server that claims a shard from a server that died fails the unfinished tasks of the shard's conversations, so their clients don't wait forever.

## Configuration

Servers read these environment variables, set in [`infra/docker-compose.yaml`](infra/docker-compose.yaml):

| Variable | Default | Meaning |
| --- | --- | --- |
| `SERVER_NAME` | host name | The server's name in the fleet |
| `PUBLIC_URL` | `http://localhost:8080` | The URL in the agent card, the load balancer's |
| `AGENT_COMMAND` | the fake agent | The ACP agent's command line |
| `SHARDS` | `64` | The number of shards; every server must use the same |
| `IDLE_TIMEOUT` | `1m` | Stops agents with no turns for this long |
| `DRAIN_TIMEOUT` | `1m` | How long a moving shard waits for its turns to end |
| `MAX_AGENTS` | `8` | Agents per server |

## Limitations

* Snapshots are whole archives, uploaded after every turn and limited to 64 MiB. Agents that append to large files would benefit from chunked uploads.
* A server that dies right after a turn completes, before the snapshot lands, loses that turn's memory.
* Clients and the servers' NATS and MySQL connections aren't authenticated.
