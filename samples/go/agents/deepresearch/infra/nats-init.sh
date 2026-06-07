#!/usr/bin/env sh
# Creates NATS JetStream streams, consumers, and KV buckets required by the
# deep research agent cluster. Intended to run inside the natsio/nats-box
# container or any environment with the `nats` CLI available.
#
# The script is idempotent: it deletes existing resources before recreating
# them so that re-running after a config change does not fail.
#
# Usage:
#   NATS_URL=nats://nats:4222 ./nats-init.sh

set -eu

NATS_URL="${NATS_URL:-nats://localhost:4222}"

echo "Waiting for NATS at ${NATS_URL}..."
sleep 2

# --- Clean up previous state ---

nats -s "${NATS_URL}" stream rm EVENTS -f 2>/dev/null || true
nats -s "${NATS_URL}" stream rm WORK   -f 2>/dev/null || true
nats -s "${NATS_URL}" stream rm STATES -f 2>/dev/null || true
nats -s "${NATS_URL}" kv rm OUTBOX_LOCK -f 2>/dev/null || true

# --- Streams ---

# Event log — durable, per-task subject.
nats -s "${NATS_URL}" stream add EVENTS \
  --subjects="events.>" \
  --retention=limits --storage=file --discard=old \
  --defaults

# Work queue — per-node-type subjects with filtered consumers.
nats -s "${NATS_URL}" stream add WORK \
  --subjects="work.>" \
  --retention=work --storage=file --discard=old \
  --defaults

# Push notifications — ephemeral signaling stream with TTL.
nats -s "${NATS_URL}" stream add STATES \
  --subjects="states.>" \
  --retention=limits --max-age=24h --storage=memory --discard=old \
  --defaults

# --- Consumers (one per agent type, filtered by subject) ---

nats -s "${NATS_URL}" consumer add WORK orchestrator \
  --filter="work.orchestrator" \
  --ack=explicit --deliver=all --replay=instant --pull \
  --defaults

nats -s "${NATS_URL}" consumer add WORK researcher \
  --filter="work.researcher" \
  --ack=explicit --deliver=all --replay=instant --pull \
  --defaults

nats -s "${NATS_URL}" consumer add WORK analyzer \
  --filter="work.analyzer" \
  --ack=explicit --deliver=all --replay=instant --pull \
  --defaults

nats -s "${NATS_URL}" consumer add WORK synthesizer \
  --filter="work.synthesizer" \
  --ack=explicit --deliver=all --replay=instant --pull \
  --defaults

# --- KV buckets ---

# Outbox leader election.
nats -s "${NATS_URL}" kv add OUTBOX_LOCK \
  --ttl=10s --storage=memory

echo "NATS streams, consumers, and KV buckets ready."
