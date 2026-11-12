# ACP fleet

A fleet of a2a-go servers behind a load balancer that runs ACP coding agents in cluster mode. Each conversation keeps its agent, its pending questions, its memory and its files when servers crash, drain or join.

![opencode agents keep their memory and files while a server crashes, a server joins and a server drains](demo/demo.gif)

Built with [a2a-go](https://github.com/a2aproject/a2a-go) and its [`a2aacp`](https://pkg.go.dev/github.com/a2aproject/a2a-go/v2/integrations/executor/a2aacp) executor.

## Overview

* Conversations are split into 64 virtual shards. Each shard is a directory with a SQLite session map, the agent homes and the scratch directories of its conversations.
* Servers own shards by rendezvous hashing. When a server joins or leaves, only its shards move.
* Any server takes any request and forwards it to the owner of the conversation's shard, so nginx needs no sticky sessions.
* Agent homes, scratch directories and the session map are saved to the NATS object store after every turn, so a crash loses no memory and no files. Scratch directories over 16 MiB move only when a shard moves gracefully.
* Every agent gets a scratch MCP server with file tools in its working directory.
* [opencode](https://opencode.ai) on Gemini runs the agents, in the image a2a-serve runs it in. A fake ACP agent runs the fleet without model keys.

## Running

1. Start NATS, MySQL, three servers with opencode agents and nginx on `:8080`. opencode uses Gemini; get a key at [Google AI Studio](https://aistudio.google.com/apikey):

   ```console
   export GEMINI_API_KEY=...
   make up-opencode
   ```

   `make up` starts the fleet with the fake agent, which needs no key.

2. Watch the fleet in one terminal:

   ```console
   make watch
   ```

3. Start a crowd of users in another:

   ```console
   make crowd N=8
   ```

   Each user asks its agent to remember a code and to keep a file of steps. Every few turns it asks for the code and the file's last line, and checks the answer.

```text
acp-fleet http://lb:8080  ·  3 servers  ·  8 conversations  ·  62 turns  ·  33 memory checks, 0 forgotten  ·  0 resent

  server-1  ● live                  25 shards   2 agents   2 conversations
  server-2  ● live                  26 shards   3 agents   3 conversations
  server-3  ● live                  13 shards   3 agents   3 conversations

  USER       SERVER     TURNS  MEMORY  NOW
  alice      server-2       8  ✓ 4     idle
  bob        server-2       9  ✓ 5     working: "Read bob.md and reply with the word on its last line only."

  16:19:01 bob      lb → server-1 → server-2       "What is the code I asked you to remember? Reply with the code only."
```

Each message reaches a random server, which forwards it to the owner of the conversation's shard.

## Try it

Crash a server while the crowd works:

```console
$ make kill S=server-2
```

```text
  server-2  ✖ no heartbeat 5s/8s    26 shards   3 agents   3 conversations
  ...
  16:19:20 server-3 took 15 shards from server-2 (crashed), 3 conversations
  16:19:20 alice's turn stopped with server-2; the message is sent again
  16:19:28 ✓ alice's agent remembers the code on server-3 after moving from server-2
```

server-3 took the shards over once server-2's heartbeat expired, restored the agent homes and scratch directories saved after the last turns, and opencode loaded its sessions. Turns that were running on server-2 fail with a message that asks to send them again, and the crowd does.

Add a server, or stop one gracefully:

```console
$ make join            # server-4 takes about a quarter of the shards; keep GEMINI_API_KEY set
$ make drain S=server-3
$ make status
SERVER    INCARNATION  STATE  SHARDS  CONVERSATIONS
server-1  2d98dd9c     live   31      2
server-4  da9f7326     live   33      0
```

A draining server lets running turns finish, saves its shards and exits.

You can also chat with the fleet yourself using the [a2a CLI](https://github.com/a2aproject/a2a-cli) v0.4.0 or later:

```console
make chat
```

`demo/record.sh` records the demo above with tmux, asciinema 3 and agg.

### The fake agent

`make up` runs a fake ACP agent that needs no model key. Every reply starts with the server that runs the agent, and it understands:

| Message | Reply |
| --- | --- |
| `save <note>` | Asks permission, then appends the note to `notes.txt` in its home |
| `scratch <text>` | Appends the text to `scratch.txt` in its scratch directory |
| `work <seconds>` | Reports a step every second until done or canceled |
| anything else | The turn number, where earlier turns ran, and what it remembers |

## How it works

| What | Where it lives | Graceful move | Crash |
| --- | --- | --- | --- |
| Session map (`sessions.db`) | SQLite in the shard directory | moves with the shard | restored from the snapshot of the last turn |
| Agent home | `homes/<context>` in the shard directory | moves with the shard | restored from the snapshot of the last turn |
| Scratch | `scratch/<context>`, the agent's working directory | moves with the shard | restored from the snapshot of the last turn; over 16 MiB lost, and the agent is told |
| Tasks | MySQL index and NATS events ([`integrations`](../../integrations)) | shared | shared |

* **Membership.** Each server rewrites its record in the `NODES` KV bucket every 2 seconds. A record expires 8 seconds after its last write, and every server sees the expiry. A server that can't write its record exits.
* **Shards.** The `SHARDS` bucket has a record per shard: the owner, an epoch, and the snapshots of its session map, homes and scratch directories in the `SHARD_DATA` object store. Every claim and save is a compare-and-swap on that record, so a server that lost a shard can't overwrite it.
* **Routing.** The work queue is `workqueue.NewPushQueue` with a router as its writer. The router finds the conversation's shard and runs the payload if this server owns it, or forwards it to the owner with NATS request/reply. While a shard moves, its payloads wait for the new owner, except answers and cancels for turns still running on the old one.
* **Agents.** The `a2aacp.Agent` restores a conversation's home and scratch directory on its first message, then starts the agent with `HOME` set to the home and the scratch directory as its working directory. opencode's config and caches are shared by the agents of a server, so a home holds only its sessions. `Config.Turn` saves the home and the scratch directory after every turn, `Config.SessionStore` reads the shard's SQLite map, and `Config.Abandoned` stores the failure of a question nobody answered.
* **Takeover.** A server that claims a shard from a server that died fails the unfinished tasks of the shard's conversations, so their clients don't wait forever.
* **Events.** Servers publish what they do on `fleet.events.*` in NATS: routed messages, turns, agents and shard moves. `make watch` draws them with the `NODES` and `SHARDS` buckets.

## Configuration

Servers read these environment variables, set in [`infra/docker-compose.yaml`](infra/docker-compose.yaml):

| Variable | Default | Meaning |
| --- | --- | --- |
| `SERVER_NAME` | host name | The server's name in the fleet |
| `PUBLIC_URL` | `http://localhost:8080` | The URL in the agent card, the load balancer's |
| `AGENT_COMMAND` | the fake agent | The ACP agent's command line |
| `FLEET_MODEL` | `google/gemini-3-flash-preview` | The opencode model, set by `make up-opencode` |
| `SHARDS` | `64` | The number of shards; every server must use the same |
| `IDLE_TIMEOUT` | `1m` | Stops agents with no turns for this long |
| `DRAIN_TIMEOUT` | `1m` | How long a moving shard waits for its turns to end |
| `MAX_AGENTS` | `8` | Agents per server |
| `SCRATCH_LIMIT_MB` | `16` | Scratch directories over this size are saved only when their shard moves gracefully |

## Limitations

* Snapshots are whole archives, uploaded after every turn and limited to 64 MiB. Agents that append to large files would benefit from chunked uploads.
* opencode runs with every tool allowed except bash, which asks. The agents share their server's container, with no sandbox between them.
* A server that dies right after a turn completes, before the snapshot lands, loses that turn's memory.
* Clients and the servers' NATS and MySQL connections aren't authenticated.
