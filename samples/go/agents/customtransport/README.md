# Custom transport example

This example demonstrates a client-side `a2aclient.Transport` and a matching
server-side HTTP binding. It uses `application/x-www-form-urlencoded` with
`id`, `role`, and `text` fields, rather than the SDK's JSON-RPC or HTTP+JSON
bindings. The server advertises `DEMO-FORM` in its AgentCard; the client
registers the same binding via `a2aclient.WithTransport` and connects with
`a2aclient.NewFromCard`.

Run from this directory:

```sh
go run .
```

Expected output:

```text
Hello from the form transport!
```

The example runs a loopback HTTP server in the same process. No model, API key,
or external service is needed. `go test ./... -count=1` exercises card
resolution, transport selection, the form exchange, and the
unsupported-operation path.

This is deliberately **not a complete A2A transport**: it handles only one
plain-text user message and a plain-text agent response. It does not support
task continuation, streaming, authentication, metadata, push notifications,
files, or multiple parts. Other `Transport` operations return
`a2a.ErrUnsupportedOperation`, and unsupported message shapes are rejected
rather than silently discarded. A production transport must implement the
full protocol, encode all supported fields, handle errors and streaming, and
supply an appropriate security boundary.

For a community implementation of an external transport rather than this
small teaching binding, see [a2a-go-fmsg](https://github.com/markmnl/a2a-go-fmsg).
