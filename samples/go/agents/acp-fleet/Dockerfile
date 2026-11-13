# Build from samples/go, so that the integration modules are in the context:
#   docker build -f agents/acp-fleet/Dockerfile .
FROM golang:1.26-alpine AS builder

WORKDIR /src
COPY integrations/mysql/go.mod integrations/mysql/go.sum integrations/mysql/
COPY integrations/nats/go.mod integrations/nats/go.sum integrations/nats/
COPY agents/acp-fleet/go.mod agents/acp-fleet/go.sum agents/acp-fleet/
WORKDIR /src/agents/acp-fleet
RUN go mod download

WORKDIR /src
COPY integrations integrations
COPY agents/acp-fleet agents/acp-fleet
WORKDIR /src/agents/acp-fleet
RUN CGO_ENABLED=0 GOOS=linux go build -o /acp-fleet .

# The fleet with the fake ACP agent, which needs no model keys.
FROM gcr.io/distroless/static:nonroot AS fake
COPY --from=builder /acp-fleet /acp-fleet
ENTRYPOINT ["/acp-fleet"]

# The fleet with opencode as the ACP agent, on the image a2a-serve runs it in.
# Agent homes keep only opencode's sessions; its config and caches are shared
# by the agents of a server, so that snapshots stay small.
FROM ghcr.io/a2aproject/harness-opencode:sha-ce681e07144c AS opencode
ENV AGENT_COMMAND="opencode acp" \
    XDG_CONFIG_HOME=/opt/opencode/config \
    XDG_CACHE_HOME=/opt/opencode/cache \
    npm_config_cache=/opt/opencode/npm
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# $schema is a JSON key, not a variable.
# hadolint ignore=SC2016
RUN mkdir -p /opt/opencode/config/opencode \
 && printf '{"$schema":"https://opencode.ai/config.json","autoupdate":false,"share":"disabled"}\n' > /opt/opencode/config/opencode/opencode.json \
 && printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1}}' \
      '{"jsonrpc":"2.0","id":2,"method":"session/new","params":{"cwd":"/tmp","mcpServers":[]}}' \
    | (cat; sleep 20) | HOME=/tmp/warm timeout 60 opencode acp > /dev/null 2>&1; \
    test -d /opt/opencode/config/opencode/node_modules \
 && rm -rf /tmp/warm \
 && chown -R node:node /opt/opencode
COPY --from=builder /acp-fleet /acp-fleet
USER 1000:1000
ENTRYPOINT ["/acp-fleet"]
