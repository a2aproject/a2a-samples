# Hello World Agent with Rate Limiting

This example demonstrates how to implement rate limiting in an A2A agent and how to use the Rate Limiting Usage Signals Extension to communicate usage information to clients.

> **📁 Location**: `samples/python/agents/helloworld_with_ratelimiter/`
>
> **📚 Extension Documentation**: See the [Rate Limiting Extension README](../../extensions/ratelimiter/) (`samples/python/extensions/ratelimiter/`) for detailed documentation and code patterns.

## Key Concepts

This example illustrates the important distinction between:

1. **Rate Limiting Enforcement** (Agent's Responsibility)
    - Always active, protects agent resources
    - Implemented directly in the agent executor
    - Happens regardless of extension activation

2. **Rate Limiting Communication** (Extension's Purpose)
    - Optional, controlled by client activation
    - Provides visibility into usage quotas
    - Helps clients make intelligent decisions

**Analogy**: The agent enforces a speed limit (rate limiting). The extension is like a speedometer - it shows you how fast you're going, but doesn't control your speed.

## What This Example Shows

- ✅ Agent **always** enforces rate limits (10 requests/minute)
- ✅ Extension activation = "Please include usage signals in responses"
- ✅ Clients can see remaining quota and retry timing when extension is activated
- ✅ Rate limiting works whether extension is activated or not
- ✅ Token bucket algorithm allows controlled burst traffic

## Architecture

### Without Extension (Basic Rate Limiting)

```text
Client Request → Agent enforces limit → Response
                        ↓
                    If exceeded: "Rate limit exceeded"
                    If allowed: "Hello World"
```

### With Extension (Rate Limiting + Signals)

```text
Client Request → Agent enforces limit → Response + Usage Signals
    (activates        ↓                       ↓
    extension)  If exceeded: "Rate limit exceeded" + {remaining: 0, retry_after: 15.3}
                If allowed: "Hello World" + {remaining: 45, limit_type: "token_bucket"}
```

## Getting Started

### 1. Start the Server

```bash
cd samples/python/agents/helloworld_with_ratelimiter
uv run .
```

The agent will start on `http://localhost:9999` with rate limiting active.

### 2. Test Without Extension

Rate limiting is enforced, but you don't get usage signals:

```bash
curl -X POST http://localhost:9999/ \
  -H "Content-Type: application/json" \
  -d '{
        "jsonrpc": "2.0",
        "id": "test",
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "messageId": "msg-1",
                "parts": [{"kind": "text", "text": "Hello"}],
                "role": "user"
            }
        }
    }'
```

Response (rate limit enforced, no usage signals):
```json
{
  "jsonrpc": "2.0",
  "id": "test",
  "result": {
    "message": {
      "kind": "message",
      "parts": [{"kind": "text", "text": "Hello World"}],
      "role": "agent"
    }
  }
}
```

### 3. Test With Extension

Same rate limiting, but now you get usage information:

```bash
curl -X POST http://localhost:9999/ \
  -H "Content-Type: application/json" \
  -H "X-A2A-Extensions: https://github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test",
    "method": "message/send",
    "params": {
      "message": {
        "kind": "message",
        "messageId": "msg-1",
        "parts": [{"kind": "text", "text": "Hello"}],
        "role": "user"
      }
    }
  }'
```

Response (same rate limiting, now with usage signals):
```json
{
  "jsonrpc": "2.0",
  "id": "test",
  "result": {
    "message": {
      "kind": "message",
      "parts": [{"kind": "text", "text": "Hello World"}],
      "role": "agent",
      "metadata": {
        "github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1/result": {
            "allowed": true,
            "remaining": 9,
            "reset_time": 1640995260.0,
            "limit_type": "token_bucket"
        }
      }
    }
  }
}
```

### 4. Test Rate Limit Exceeded

Make multiple rapid requests to trigger rate limiting:

```bash
# Run this multiple times quickly
for i in {1..15}; do
  curl -X POST http://localhost:9999/ \
    -H "Content-Type: application/json" \
    -H "X-A2A-Extensions: https://github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1" \
    -d '{
      "jsonrpc": "2.0",
      "id": "test-'$i'",
      "method": "message/send",
      "params": {
        "message": {
            "kind": "message",
            "messageId": "msg-'$i'",
            "parts": [{"kind": "text", "text": "Hello"}],
            "role": "user"
        }
      }
    }'
  echo ""
done
```

After exceeding the limit, you'll see:

```json
{
  "jsonrpc": "2.0",
  "id": "test-11",
  "result": {
    "message": {
      "kind": "message",
      "parts": [{
        "kind": "text",
        "text": "Rate limit exceeded. 0 requests remaining. Retry after 15.3 seconds."
      }],
      "role": "agent",
      "metadata": {
        "github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1/result": {
            "allowed": false,
            "remaining": 0,
            "retry_after": 15.3,
            "limit_type": "token_bucket"
        }
      }
    }
  }
}
```

## Testing with Provided Scripts

### Basic Client Test

```bash
uv run test_client.py
```

This runs a standard A2A client that makes requests to the agent.

### Rate Limiting Test Suite

```bash
uv run rate_limit_test.py
```

This demonstrates rate limiting behavior by:
- Making rapid requests to trigger limits
- Showing enforcement works without extension
- Showing extension provides visibility
- Testing recovery after waiting

Run specific tests:
```bash
# Test basic rate limiting (without extension)
uv run rate_limit_test.py --test basic

# Test with extension signals
uv run rate_limit_test.py --test extension

# Test rate limit recovery (token refill)
uv run rate_limit_test.py --test recovery
```

## Rate Limiting Configuration

### Default Limits

- **Rate**: 10 requests per minute
- **Algorithm**: Token bucket with 2x capacity multiplier
- **Burst capacity**: 20 requests (allows initial burst, then sustained rate)
- **Identification**: By IP address (for demo; use OAuth/API keys in production)

### How Token Bucket Works

```text
Bucket capacity: 20 tokens (10 requests × 2.0 multiplier)
Refill rate: 10 tokens per minute (0.167 tokens/second)

Timeline:
t=0s:  20 tokens available → Can make 20 requests immediately
t=10s: 21 tokens available → Refilled 1-2 tokens
t=60s: 20 tokens available → Back to capacity (max)

Behavior:
- Allows burst of 20 requests
- Then limits to 10 requests/minute sustained
- Fair to both bursty and steady traffic
```

## Code Walkthrough

### Agent Executor (`agent_executor.py`)

The executor shows the minimal changes needed to add rate limiting to a basic HelloWorld agent:

```python
class HelloWorldAgentExecutor(AgentExecutor):
    def __init__(self, rate_limiter, rate_limit_extension):
        self.agent = HelloWorldAgent()
        self.rate_limiter = rate_limiter           # For enforcement
        self.rate_limit_extension = rate_limit_extension  # For communication

    async def execute(self, context, event_queue):
        # Step 1: Extract client identity
        client_key = self._extract_client_key(context)

        # Step 2: ALWAYS enforce rate limits (10 requests/minute)
        usage = self.rate_limiter.check_limit(client_key, limit=10, window=60)

        # Step 3: If rate limited, return error
        if not usage.allowed:
            message = new_agent_text_message("Rate limit exceeded...")

            # Extension: Add signals IF client requested them
            if self.rate_limit_extension.is_activated(context):
                self.rate_limit_extension.add_usage_signals(message, usage)

            await event_queue.enqueue_event(message)
            return

        # Step 4: Process request normally
        result = await self.agent.invoke()
        message = new_agent_text_message(result)

        # Extension: Add signals IF client requested them
        if self.rate_limit_extension.is_activated(context):
            self.rate_limit_extension.add_usage_signals(message, usage)

        await event_queue.enqueue_event(message)
```

**Key Differences from Basic HelloWorld:**
- Added rate limiter and extension to `__init__`
- Added client identification step
- Added rate limit check before processing
- Conditionally add usage signals based on extension activation

### Server Setup (`__main__.py`)

```python
# Separate initialization: enforcement vs communication
rate_limiter = TokenBucketLimiter(capacity_multiplier=2.0)  # Enforcement
rate_limit_extension = RateLimitingExtension()  # Communication

# Advertise extension capability
agent_card = rate_limit_extension.add_to_card(agent_card)

# Create executor with both components
executor = HelloWorldAgentExecutor(
    rate_limiter=rate_limiter,
    rate_limit_extension=rate_limit_extension
)
```

## Understanding the Extension

### What the Extension IS

- ✅ A communication protocol for usage signals
- ✅ Optional (client decides whether to activate)
- ✅ Informational (helps clients make decisions)
- ✅ Standardized metadata format

### What the Extension is NOT

- ❌ Rate limiting enforcement (agent does this)
- ❌ Required for rate limiting to work
- ❌ A way for clients to control limits
- ❌ Client-side rate limiting

### Extension Activation Flow

```text
1. Agent advertises extension in AgentCard
    → "I can send rate limit usage signals"

2. Client includes extension URI in X-A2A-Extensions header
    → "I understand rate limit signals, please include them"

3. Agent checks is_activated(context)
    → Returns True if client requested signals

4. Agent adds usage signals to response metadata
    → Client receives detailed usage information
```

## Production Considerations

This example uses simplified approaches for demonstration. For production:

**❌ Don't use IP addresses for client identity**
```python
client_key = f"ip:{context.remote_addr}"  # Can be spoofed, shared
```

**✅ Use authenticated identity instead**
```python
def _extract_client_key(self, context):
    token = self._verify_oauth_token(context.authorization)
    return f"user:{token.user_id}"
```

**❌ Don't use in-memory rate limiters in distributed systems**
```python
rate_limiter = TokenBucketLimiter()  # Lost on restart, not shared across instances
```

**✅ Use distributed rate limiter (Redis, etc.)**
```python
from limits import RateLimitItemPerSecond
from limits.storage import RedisStorage
storage = RedisStorage("redis://localhost:6379")
```

See the [extension's production patterns](../../extensions/ratelimiter/examples/production_patterns.py) for complete examples.

## Build Container Image

You can containerize the agent:

```bash
cd samples/python/agents/helloworld_with_ratelimiter
podman build . -t helloworld-ratelimiter-a2a-server
podman run -p 9999:9999 helloworld-ratelimiter-a2a-server
```

## Validate with A2A CLI

Test with the official A2A CLI client:

```bash
cd samples/python/hosts/cli
uv run . --agent http://localhost:9999
```

## Comparison with Basic HelloWorld

| Aspect                   | Basic HelloWorld | With Rate Limiting                      |
| ------------------------ | ---------------- | --------------------------------------- |
| **Request Handling**     | Unlimited        | 10 requests/minute                      |
| **Resource Protection**  | None             | Token bucket enforcement                |
| **Usage Visibility**     | None             | Optional via extension                  |
| **Burst Traffic**        | Accepted         | Controlled (20 initial, then 10/min)    |
| **Production Ready**     | Demo only        | Closer to production patterns           |

## Key Takeaways

1. **Enforcement is separate from communication**
    - Agent always enforces limits
    - Extension optionally communicates usage

2. **Extension activation is client-driven**
    - Client says "I want usage info"
    - Agent decides whether to enforce (always yes)

3. **Server controls policies**
    - Server determines rate limits
    - Server extracts client identity
    - Client cannot set their own limits

4. **Token bucket allows bursts**
    - Good for real-world traffic patterns
    - Balances burst and sustained rates

## Next Steps

- Read the extension documentation in `samples/python/extensions/ratelimiter/README.md`
- Explore production rate limiting libraries (python-limits, slowapi, etc.)
- Implement authentication-based client identification
- Add distributed rate limiting with Redis
- Monitor rate limit metrics in production

## Disclaimer

This sample demonstrates A2A protocol extension patterns and rate limiting concepts. For production use, consider:

- Persistent storage backends (Redis, database)
- Distributed rate limiting across multiple instances
- Authentication and authorization (OAuth, API keys)
- Monitoring and alerting integration
- Custom rate limiting policies per use case

**Important**: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.
