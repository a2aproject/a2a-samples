# Build from samples/go, so that the integration modules are in the context:
#   docker build -f agents/deepresearch/Dockerfile .
FROM golang:1.26-alpine AS builder

WORKDIR /src

COPY integrations/mysql/go.mod integrations/mysql/go.sum integrations/mysql/
COPY integrations/nats/go.mod integrations/nats/go.sum integrations/nats/
COPY agents/deepresearch/go.mod agents/deepresearch/go.sum agents/deepresearch/
WORKDIR /src/agents/deepresearch
RUN go mod download

WORKDIR /src
COPY integrations integrations
COPY agents/deepresearch agents/deepresearch
WORKDIR /src/agents/deepresearch
RUN CGO_ENABLED=0 GOOS=linux go build -o /deepresearch .

FROM gcr.io/distroless/static:nonroot
COPY --from=builder /deepresearch /deepresearch
ENTRYPOINT ["/deepresearch"]
