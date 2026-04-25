# Blueprint Governed Agent — A2A Example

A minimal Python agent built with `a2a-sdk==1.0.2` that demonstrates how to enforce
[AI Design Blueprint](https://aidesignblueprint.com) governance principles using native A2A protocol primitives.

## What this demonstrates

Three principles from the Blueprint, mapped directly to A2A mechanics:

| Blueprint Principle | A2A Primitive |
|---|---|
| **Explicit approval before destructive actions** (P8) | `TASK_STATE_INPUT_REQUIRED` — agent pauses, surfaces confirmation request, resumes on user response |
| **Perceptible background work** (P5) | `TaskStatusUpdateEvent` streaming — intermediate `working` events emitted at each execution step |
| **Mid-task steering — cancellation** (P7) | `cancel()` handler + approval-gate flow that honours any non-confirm response |

These are the exact three principles the OpenClaw inbox incident violated
([full teardown](https://aidesignblueprint.com/en/principles)).

## Quick start

```bash
cd a2a/
uv run python __main__.py &      # start agent on :9999
uv run python test_client.py     # run all 3 assertions
```

Expected output:
```
AI Design Blueprint — A2A governance validation

Connecting to agent at http://127.0.0.1:9999 ...
Agent card found: Blueprint Governed Agent

  [1] Approval gate... PASS  (state='TASK_STATE_INPUT_REQUIRED', context_id=abc12345...)
  [2] Mid-task steering (cancel)... PASS  (state='TASK_STATE_CANCELED')
  [3] Streaming + confirm... PASS  (3 working event(s) → completed, 5 total events)

All 3 assertions passed.
```

## Agent flow

```
User: "delete /tmp/test.txt"
  ↓
Agent: [task: working] Resetting state...
  ↓
Agent: [input-required] "This will permanently delete the file. Reply 'confirm' to proceed."
  ↓
User: "confirm" (with taskId + contextId)
  ↓
Agent: [working] Confirmed. Validating target path...
Agent: [working] Executing file deletion...
Agent: [completed] File deleted successfully.

— or —

User: "abort" (or anything except 'confirm')
  ↓
Agent: [canceled] Action aborted — file was not modified.
```

## Files

```
a2a/
├── pyproject.toml      # a2a-sdk==1.0.2, uvicorn, httpx, protobuf==5.29.5
├── README.md           # this file
├── __main__.py         # AgentCard + Starlette server setup
├── agent_executor.py   # GovernedFileAgent: approval gate + streaming + cancel
└── test_client.py      # validates all 3 Blueprint principles end-to-end
```

## Implementation notes

- **`protobuf==5.29.5`** is pinned — protobuf 7.x removed `FieldDescriptor.label` from its upb backend, breaking the a2a-sdk's internal proto introspection. The SDK specifies `>=5.29.5` as its minimum; pin to this version to avoid the regression.
- **Task enqueue on every `execute()` call** — the SDK's `ActiveTask` consumer requires a `Task` object as the first event in the queue. On resume (when `context.current_task` is not `None`), the existing task is re-enqueued with its status reset to `WORKING` to clear the stale `INPUT_REQUIRED` state before new status events are emitted.
- **Resume detection** — `context.current_task is None` distinguishes a first call from a resume. On first call, a new task is created via `new_task_from_user_message(context.message)`.
- **`taskId` required for resume** — clients must include both `contextId` and `taskId` in the resume message so the server routes the request to the correct `ActiveTask`.

## Connection to the Teams tier

This example is a community contribution to the A2A ecosystem. It also proves the
architecture for the Blueprint Teams tier feature: **Blueprint coach as an A2A peer agent**.

In the Teams scenario, production agents (LangGraph, CrewAI, AutoGen) call the Blueprint
coach during their own workflows — governance runs automatically, without human intervention.

- **Basic**: Human reads MCP doctrine in their IDE
- **Pro**: Human submits code, `architect.validate` returns violations
- **Teams** _(coming soon)_: Production agents call Blueprint coach as an A2A peer

## Resources

- [AI Design Blueprint](https://aidesignblueprint.com)
- [Blueprint MCP endpoint](https://aidesignblueprint.com/mcp)
- [Agent assets](https://aidesignblueprint.com/en/for-agents)
- [A2A protocol](https://a2aproject.github.io/A2A/)
