# A2A Timestamp Extension Showcase

This package implements the **Timestamp Extension** for the A2A SDK in Python.

The extension showcases how to enrich outgoing A2A messages and artifacts with compliance timestamps in a modular, decoupled, and highly automated manner.

---

## Architecture & Package Structure

The package is split into separate modules to isolate concerns and prevent client-side dependencies from bloating server-side or core stamping utilities:

* **`timestamp_ext/core.py`**: Houses the core metadata (`URI`, `TIMESTAMP_FIELD`) and the main `TimestampExtension` helper class.
* **`timestamp_ext/server.py`**: Houses server-side decorators (`_TimestampingAgentExecutor`, `_TimestampingEventQueue`) and the public `wrap_executor` function.
* **`timestamp_ext/client.py`**: Houses client-side interceptors, decorators, and factory wrappers (`wrap_client_factory`, `client_interceptor`). It isolates all client-specific Protobuf imports.
* **`timestamp_ext/__init__.py`**: Exposes only the core public exports for general usage.

---

## Usage Guide

### 1. Server-Side Setup

To enable the timestamp extension on your A2A agent, advertise support in the `AgentCard` and wrap the executor using `wrap_executor`:

```python
from a2a.types.a2a_pb2 import AgentCard
from timestamp_ext.core import TimestampExtension
from timestamp_ext.server import wrap_executor

# 1. Initialize the extension
ext = TimestampExtension()

# 2. Advertise support on the agent card
card = AgentCard(...)
ext.add_to_card(card=card)

# 3. Decorate your agent executor
handler = DefaultRequestHandler(
    agent_executor=wrap_executor(executor=MyExecutor(), ext=ext),
    agent_card=card,
    ...
)
```

With this single wrapper, any message or artifact emitted by `MyExecutor` is automatically stamped with the current UTC ISO timestamp when requested by the client.

### 2. Client-Side Setup

To request the extension from a server and read timestamps, wrap your `ClientFactory` using `wrap_client_factory`:

```python
from a2a.client import ClientConfig, ClientFactory
from timestamp_ext.core import TimestampExtension
from timestamp_ext.client import wrap_client_factory

# 1. Initialize the extension
ext = TimestampExtension()

# 2. Wrap the client factory
factory = wrap_client_factory(
    factory=ClientFactory(config=ClientConfig(httpx_client=httpx_client)),
    ext=ext
)
client = factory.create(card=card)
```

The wrapped factory installs a client interceptor that automatically adds the `A2A-Extensions: <uri>` header to every outgoing call and stamps client-side messages.

---

## Running the Showcase & Tests

### Prerequisites

Ensure you have `uv` installed and sync the development dependencies:

```bash
uv sync --group dev
```

### Running the Showcase Server Standalone

You can start the Starlette ASGI server hosting the Echo agent and the wrapped executor:

```bash
uv run python -m tests
```

The server will start running on `http://127.0.0.1:9998`.

### Running the Integration Tests

Run the end-to-end integration tests (which spin up the server in a subprocess and execute client queries):

```bash
uv run pytest -s -v
```
