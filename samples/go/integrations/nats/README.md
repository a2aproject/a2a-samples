# NATS integration

This Go module implements a2a-go server extension points on NATS JetStream for the Go samples.

| Package | Contents |
| --- | --- |
| `msgstream` | Event queues on the `EVENTS` stream, a pull work queue on the `WORK` stream, and a push notification sender |
| `lease` | Leader election on a KV bucket |
| `natstest` | Helpers that connect integration tests to NATS and reset streams and buckets |

Samples use the module through a `replace` directive in their `go.mod`:

```text
replace github.com/a2aproject/a2a-samples/samples/go/integrations/nats => ../../integrations/nats
```

The streams and their consumers are created by the deployment. See [`deepresearch/infra/nats-init.sh`](../../agents/deepresearch/infra/nats-init.sh) for an example.

Run the integration tests with `go test ./itest/`. They use a NATS server on `localhost:4222`, and start the one in `compose.yaml` if none is running.
