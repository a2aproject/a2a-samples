# A2A4J Client Hello World Sample

This is a sample A2A (Agent2Agent) protocol client implementation demonstrating how to use the A2A4J framework to interact with an A2A server.

## Features

- ✅ A2A protocol client implementation
- ✅ JSON-RPC 2.0 synchronous and streaming communication
- ✅ Example of sending messages to an A2A server
- ✅ Real-time status updates and progress tracking
- ✅ Detailed logging

## Quick Start

> **Before running the client, please make sure the `server-hello-world` module is started and running on http://localhost:8089.**

### Prerequisites

- Java 17 or higher
- Maven 3.6 or higher

### Build Project

```bash
# Clone repository (if you haven't already)
git clone git@github.com:google-a2a/a2a-samples.git
cd a2a-samples/samples/a2a4j-springboot-samples/

# Build entire project
mvn clean install

# Navigate to sample client directory
cd client-hello-world
```

### Run Client

```bash
# Run with Maven
mvn spring-boot:run

# Or run compiled JAR
mvn clean package
java -jar target/client-hello-world-*.jar
```

### Example Usage

The client will attempt to connect to the A2A server (default: http://localhost:8089) and send a sample message. You can modify the message and server URL in the configuration file.

---

For more details, see the source code and comments.
