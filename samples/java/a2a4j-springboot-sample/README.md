# A2A4J Spring Boot Sample Project

This is an A2A (Agent2Agent) protocol implementation sample project that demonstrates how to build intelligent agent servers and clients using the [A2A4j](https://github.com/a2ap/a2a4j) with [SpringBoot](https://github.com/spring-projects/spring-boot) framework.  
The project consists of two main modules: server and client examples.

## Project Structure

```
a2a4j-springboot-sample/
├── client-hello-world/    # Client example module
└── server-hello-world/    # Server example module
```

## Features

### Server Features
- ✅ Complete A2A protocol implementation
- ✅ JSON-RPC 2.0 synchronous and streaming communication
- ✅ Automatic Agent Card discovery
- ✅ Multiple artifact type generation (text, code, summaries)
- ✅ Real-time status updates and progress tracking
- ✅ Server-Sent Events streaming responses
- ✅ CORS cross-origin support
- ✅ Detailed logging

### Client Features
- ✅ A2A protocol client implementation
- ✅ JSON-RPC 2.0 synchronous and streaming communication
- ✅ Example message sending
- ✅ Real-time status updates and progress tracking
- ✅ Detailed logging

## Quick Start

### Prerequisites

- Java 17 or higher
- Maven 3.6 or higher
- curl or other HTTP client (for testing)

### Build Project

```bash
# Clone repository (if you haven't already)
git clone git@github.com:google-a2a/a2a-samples.git
cd a2a-samples/samples/a2a4j-springboot-samples/

# Build entire project
mvn clean install
```

### Run Server

```bash
# Navigate to server example directory
cd server-hello-world

# Run with Maven
mvn spring-boot:run

# Or run compiled JAR
mvn clean package
java -jar target/server-hello-world-*.jar
```

The server will start at **http://localhost:8089**.

### Run Client

```bash
# Navigate to client example directory
cd client-hello-world

# Run with Maven
mvn spring-boot:run

# Or run compiled JAR
mvn clean package
java -jar target/client-hello-world-*.jar
```

## Testing the Server

### Verify Server Status

```bash
# Check if server is running
curl -X GET http://localhost:8089/actuator/health

# Expected response
{"status":"UP"}
```

### A2A Protocol Endpoint Testing

#### 1. Agent Card Discovery

Get agent capabilities and metadata information:

```bash
curl -X GET http://localhost:8089/.well-known/agent.json
```

#### 2. Synchronous Message Sending

Send a message and wait for complete response:

```bash
curl -X POST http://localhost:8089/a2a/server \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {
            "kind": "text",
            "text": "Please help me analyze basic machine learning concepts"
          }
        ],
        "messageId": "9229e770-767c-417b-a0b0-f0741243c589"
      }
    },
    "id": "1"
  }'
```

#### 3. Streaming Message Sending

Send a message and receive real-time updates:

```bash
curl -X POST http://localhost:8089/a2a/server \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/stream",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {
            "kind": "text",
            "text": "Generate a simple Java class example"
          }
        ],
        "messageId": "9229e770-767c-417b-a0b0-f0741243c583"
      }
    },
    "id": "1"
  }'
```

## Configuration

### Server Configuration

Configure in `server-hello-world/src/main/resources/application.yml`:

```yaml
server:
  port: 8089  # Modify server port
  
a2a:
  server:
    id: "server-hello-world"
    name: "A2A Java Server"
    description: "A sample A2A agent implemented in Java"
    version: "1.0.0"
    url: "http://localhost:${server.port}/a2a/server"
    provider:
      name: "A2A"
      url: "https://github.com/google-a2a/a2a-samples"
    documentationUrl: "https://google-a2a.github.io/A2A/"
    capabilities:
      streaming: true
      pushNotifications: false
      stateTransitionHistory: true
    defaultInputModes:
      - "text"
    defaultOutputModes:
      - "text"
    skills:
      - name: "hello-world"
        description: "A simple hello world skill"
        tags:
          - "greeting"
          - "basic"
        examples:
          - "Say hello to me"
          - "Greet me"
        inputModes:
          - "text"
        outputModes:
          - "text"
```

## Extension Development

### Custom Your Agent Executor

Create your own `AgentExecutor` implementation:

```java
@Component
public class MyCustomExecutor implements AgentExecutor {
    
    @Override
    public Mono<Void> execute(RequestContext context, EventQueue eventQueue) {
        // Implement custom logic
        return Mono.empty();
    }
    
    @Override
    public Mono<Void> cancel(String taskId) {
        // Implement cancellation logic
        return Mono.empty();
    }
}
```

### Add Custom Endpoints

Extend controller to support more functionality:

```java
@RestController
public class CustomController {
    
    @GetMapping("/custom/endpoint")
    public ResponseEntity<String> customEndpoint() {
        return ResponseEntity.ok("Custom response");
    }
}
```

## Troubleshooting

### Common Issues

1. **Port in use**: Modify `server.port` in `application.yml`
2. **Java version incompatible**: Ensure using Java 17 or higher
3. **Dependency issues**: Run `mvn clean install` to rebuild

### Debug Mode

Enable detailed logging:

```yaml
logging:
  level:
    io.github.a2ap: DEBUG
    org.springframework.web: DEBUG
```

## Production Deployment

### Docker Deployment

```dockerfile
FROM openjdk:17-jre-slim
COPY target/server-hello-world-*.jar app.jar
EXPOSE 8089
ENTRYPOINT ["java", "-jar", "/app.jar"]
```

## References

- [A2A Protocol Specification](https://google-a2a.github.io/A2A/specification/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [A2A4J Core Documentation](https://github.com/a2ap/a2a4j/tree/main/a2a4j-core)
- [Spring Boot Starter Documentation](https://github.com/a2ap/a2a4j/tree/main/a2a4j-spring-boot-starter/a2a4j-server-spring-boot-starter)

## License

This project is licensed under the Apache License 2.0
