# A2A Timestamp Extension Showcase

This package implements the **Timestamp Extension** for the A2A SDK in Python.

The extension showcases how to enrich outgoing A2A messages and artifacts with compliance timestamps in a modular, decoupled, and highly automated manner.

---

## Architecture & Package Structure

The package is split into separate modules to isolate concerns and prevent client-side dependencies from bloating server-side or core stamping utilities:

* **`core.py`**: Houses the core metadata (`URI`, `TIMESTAMP_FIELD`) and the main `TimestampExtension` helper class.
* **`server.py`**: Houses server-side decorators (`_TimestampingAgentExecutor`, `_TimestampingEventQueue`) and the public `wrap_executor` function.
* **`client.py`**: Houses client-side interceptors, decorators, and factory wrappers (`wrap_client_factory`, `client_interceptor`). It isolates all client-specific Protobuf imports.
* **`__init__.py`**: Exposes only the core public exports for general usage.

---

## Usage Guide

### 1. Server-Side Setup

To enable the timestamp extension on your A2A agent, advertise support in the `AgentCard` and wrap the executor using `wrap_executor`:

```python
from a2a.types.a2a_pb2 import AgentCard
from timestamp.core import TimestampExtension
from timestamp.server import wrap_executor

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
from timestamp.core import TimestampExtension
from timestamp.client import wrap_client_factory

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

- **Python**: Version 3.10 or higher.

### Quick Start

1. **Set up a Virtual Environment and Install Dependencies**

   Create and activate a virtual environment, then install the required packages:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Start the Server**

   Run the A2A agent server locally on port `9998`:

   ```bash
   python -m tests
   ```

3. **Run the Interactive Demo Client**

   In a separate terminal, activate the virtual environment and run the client to interact with the server:

   ```bash
   source .venv/bin/activate
   python tests/test_client.py
   ```

### Running the Integration Tests

Run the end-to-end integration tests (which spin up the server in a subprocess and execute client queries):

```bash
pytest -s -v
```

