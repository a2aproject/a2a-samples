# A2A Timestamp Extension Showcase (JavaScript/TypeScript)

This package implements the **Timestamp Extension** for the `@a2a-js/sdk` in JavaScript/TypeScript.

The extension showcases how to enrich outgoing A2A messages and artifacts with compliance timestamps in a modular, decoupled, and highly automated manner.

---

## Architecture & Package Structure

The package is split into separate modules to isolate concerns and prevent client-side dependencies from bloating server-side or core stamping utilities:

- **`timestamp_ext/core.ts`**: Houses the core metadata (`URI`, `TIMESTAMP_FIELD`) and the main `TimestampExtension` helper class.
- **`timestamp_ext/server.ts`**: Houses the public `wrapExecutor` function that intercepts agent execution to stamp outgoing events.
- **`timestamp_ext/client.ts`**: Houses client-side interceptors, decorators, and factory wrappers (`wrapClientFactory`, `clientInterceptor`).
- **`timestamp_ext/index.ts`**: Exposes only the core public exports for general usage.
- **`index.ts`**: Configures and launches the Express web server demonstrating the timestamp extension on an Echo agent.
- **`agent_executor.ts`**: Implements the A2A agent executor class (`EchoExecutor`) and the `EchoAgent` to process and echo text requests.
- **`test_client.ts`**: An integration test client demonstrating how to wrap a client factory, send a message, and validate stamped response metadata.

---

## Usage Guide

### 1. Server-Side Setup

To enable the timestamp extension on your A2A agent, advertise support in the `AgentCard` and wrap the executor using `wrapExecutor`:

```typescript
import { AgentCard } from "@a2a-js/sdk";
import { TimestampExtension } from "./timestamp_ext/index.js";
import { wrapExecutor } from "./timestamp_ext/index.js";

// 1. Initialize the extension
const ext = new TimestampExtension();

// 2. Advertise support on the agent card
const card = ext.addToCard(baseCard);

// 3. Decorate your agent executor
const requestHandler = new DefaultRequestHandler(
    card,
    new InMemoryTaskStore(),
    wrapExecutor(new MyExecutor(), ext),
    new DefaultExecutionEventBusManager()
);
```

With this single wrapper, any message or artifact emitted by `MyExecutor` is automatically stamped with the current UTC ISO timestamp when requested by the client.

### 2. Client-Side Setup

To request the extension from a server and read timestamps, wrap your `ClientFactory` using `wrapClientFactory`:

```typescript
import { ClientFactory } from "@a2a-js/sdk/client";
import { TimestampExtension } from "./timestamp_ext/index.js";
import { wrapClientFactory } from "./timestamp_ext/index.js";

// 1. Initialize the extension
const ext = new TimestampExtension();

// 2. Wrap the client factory
const factory = wrapClientFactory(
    new ClientFactory({ transports: [new JsonRpcTransportFactory()] }),
    ext
);
const client = await factory.createFromAgentCard(card);
```

The wrapped factory installs a client interceptor that automatically adds the `A2A-Extensions: <uri>` header to every outgoing call and stamps client-side messages.

---

## Running the Showcase & Tests

### Prerequisites

Install the development dependencies:

```bash
npm install
```

### Running the Showcase Server Standalone

You can start the Express server hosting the Echo agent and the wrapped executor. To match the fixed clock verification expected by the integration client test, start the server with the `TIMESTAMP_EXT_FIXED_CLOCK` environment variable:

```bash
TIMESTAMP_EXT_FIXED_CLOCK=1700000000 npm start
```

The server will start running on `http://127.0.0.1:9998`.

### Running the Integration Client

In a separate terminal window, run the integration client (which resolves the card, wraps the factory, calls the running server, and validates the timestamps):

```bash
npm run client
```
