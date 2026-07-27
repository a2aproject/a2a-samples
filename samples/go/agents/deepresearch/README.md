# Deep Research

A multi-agent system that performs deep research on a given topic. The project showcases how to implement standard `a2a` SDK interfaces to build a scalable, fault-tolerant agent cluster using MySQL and NATS.

Built using [a2a-go](https://github.com/a2aproject/a2a-go) and [adk](https://github.com/google/adk-go).

## Overview

*   Role-Based Agent Cluster: Horizontally scalable cluster of orchestrator, researcher, analyzer, and synthesizer roles.
*   Infrastructure Separation: MySQL for task indexing/outbox, and NATS JetStream for event log streaming (`EVENTS`) and work queues (`WORK`)
*   `a2a` Push Notifications: Workers use push notifications to signal completion, avoiding polling.
*   Fault-Tolerant Checkpointing: Event sourcing to replay progress from NATS and resume cleanly after crashes.

<img src="./assets/deepresearch.png" width="740" alt="Deep research agent architecture diagram"/>

## Running

1. Setup your environment variables:
   ```bash
   cp .example.env .env
   # Open .env and configure your GOOGLE_API_KEY
   ```

2. Start the full dockerized stack (NATS, MySQL, nginx load balancer, and agent replicas):
   ```bash
   make up
   ```

3. Submit a test research request to the orchestrator via the `a2a` CLI:
   ```bash
   make send
   ```

## Details

The Orchestrator agent coordinates the entire research request lifecycle through sequential stages:

1.  Planning: An LLM planner decomposes the user's initial question into 3–5 independent subtask messages.
2.  Initial Research: The orchestrator dispatches these subtasks to the Researcher workers. The researchers run Google Search tools, save findings as task artifacts in NATS, and report completion via push notifications.
3.  Analysis: The orchestrator dispatches the research task IDs as `ReferenceTasks` to the Analyzer. The Analyzer decorator fetches the findings from the NATS `EVENTS` stream by ID to check for contradictions and gaps.
4.  Follow-up Research: The orchestrator triggers a targeted second round of research to resolve contradictions and gaps.
5.  Synthesis: The orchestrator dispatches all research task references as `ReferenceTasks` to the Synthesizer. The Synthesizer similarly fetches the findings from NATS by ID, compiles a unified HTML report, and writes it to the store.
6.  Completion: The orchestrator returns the final HTML report URL to the user and marks the task as completed.

### `a2a` Communication and Storage Patterns

*   Task References: Downstream agents (Analyzer and Synthesizer) **do not** receive large text payloads. Instead, they receive a list of task IDs (`ReferenceTasks`) in the request, and use a decorator to fetch the corresponding raw artifacts from the NATS `EVENTS` stream before executing.
*   Transactional Outbox: To guarantee database and message queue consistency, inserting task updates and writing outbox records happen in a single SQL transaction. A leader-elected outbox daemon polls MySQL and publishes events to NATS.
*   Event-Sourced Replay: If the orchestrator node restarts, it reconstructs its internal stage checklist state (replaying events like `MessagePrepare` and `MessageCommit` from NATS `STATES` stream) to resume the workflow from the exact stage where it left off.

<img src="./assets/sample_output.png" width="740" alt="Sample output of the deep research agent"/>
