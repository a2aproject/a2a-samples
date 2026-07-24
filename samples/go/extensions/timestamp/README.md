# A2A Timestamp Extension Showcase

This package implements the **Timestamp Extension** for the A2A SDK in Go (`a2a-go/v2`).

The extension showcases how to enrich outgoing A2A messages and artifacts with compliance timestamps in a modular, decoupled, and highly automated manner.

---

## Architecture & Package Structure

The package is structured to isolate library concerns from runnable demonstration code:

* **`timestamp_ext/`**: The core library package.
  * **`core.go`**: Houses the core metadata (`URI`, `TimestampField`), the main `TimestampExtension` struct, and functional options (`WithClock`).
  * **`server.go`**: Houses server-side interceptors (`ServerInterceptor`, `NewServerInterceptor`) and `WrapExecutor`.
  * **`client.go`**: Houses client-side interceptors (`ClientInterceptor`).
* **`main.go`**: Configures and launches the HTTP agent server on port `9998`.
* **`agent_executor.go`**: Implements the `echoExecutor` and `echoAgent` to process and echo text requests.
* **`client_test.go`**: Contains end-to-end integration tests verifying the client-server round trip and compliance timestamps.

---

## Usage Guide

### 1. Server-Side Setup

To enable the timestamp extension on your A2A agent, advertise support in the `AgentCard`, attach `ServerInterceptor`, and wrap the executor using `WrapExecutor`:

```go
import (
	"samples/go/extensions/timestamp/timestamp_ext"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
)

// 1. Initialize the extension (optionally with a custom clock)
ext := timestamp_ext.NewTimestampExtension()

// 2. Advertise support on the agent card
card := ext.AddToCard(&a2a.AgentCard{ ... })

// 3. Setup handler with interceptor & wrapped executor
handler := a2asrv.NewHandler(
	timestamp_ext.WrapExecutor(&MyExecutor{}, ext),
	a2asrv.WithExecutorContextInterceptor(timestamp_ext.NewServerInterceptor(ext)),
)
```

With this setup, any message or artifact emitted by `MyExecutor` is automatically stamped with the current UTC ISO timestamp when requested by the client.

### 2. Client-Side Setup

To request the extension from a server and read timestamps, pass `ClientInterceptor` when creating your `Client`:

```go
import (
	"samples/go/extensions/timestamp/timestamp_ext"

	"github.com/a2aproject/a2a-go/v2/a2aclient"
)

// 1. Initialize the extension
ext := timestamp_ext.NewTimestampExtension()

// 2. Create client with interceptor
client, err := a2aclient.NewFromCard(ctx, card, a2aclient.WithCallInterceptors(timestamp_ext.ClientInterceptor(ext)))
```

The installed interceptor automatically adds the `A2A-Extensions: <uri>` header to every outgoing call and stamps client-side messages.

---

## Running the Showcase Server Standalone

You can start the standalone HTTP server hosting the Echo agent:

```bash
go run .
```

The server will start running on `http://127.0.0.1:9998`.

## Running Tests

Run the integration tests:

```bash
go test -v ./...
```

