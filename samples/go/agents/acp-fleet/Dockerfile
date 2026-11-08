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

# The fleet with Gemini CLI as the ACP agent.
FROM node:22-slim AS gemini
RUN npm install -g @google/gemini-cli && npm cache clean --force
COPY --from=builder /acp-fleet /acp-fleet
USER node
ENTRYPOINT ["/acp-fleet"]
