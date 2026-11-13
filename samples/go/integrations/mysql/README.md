# MySQL integration

This Go module implements the a2a-go task store on MySQL for the Go samples.

| Package | Contents |
| --- | --- |
| `store` | A task store that indexes tasks in MySQL and materializes them from an event stream, and a transactional outbox that relays task events to that stream |
| `mysqltest` | A helper that connects integration tests to MySQL and recreates the tables |

The store reads events with an a2a-go `eventqueue.Manager`, and the outbox publishes them with an `eventqueue.Writer`. The relay runs on one server at a time, elected by a `store.Leader`. The [NATS integration](../nats) provides all three.

[`store/schema.sql`](store/schema.sql) creates the tables. Deployments run it when MySQL starts, for example from `/docker-entrypoint-initdb.d`.

Samples use the module through `replace` directives in their `go.mod`:

```text
replace github.com/a2aproject/a2a-samples/samples/go/integrations/mysql => ../../integrations/mysql
```

Run the integration tests with `go test ./itest/`. They use NATS on `localhost:4222` and MySQL on `localhost:3306`, and start the ones in `compose.yaml` if either is not running.
