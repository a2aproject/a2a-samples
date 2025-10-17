# Hello World Agent with Rate Limiting Extension

This example demonstrates how to integrate the A2A Rate Limiting Extension with a HelloWorld agent. It showcases the complete implementation of rate limiting using the official A2A extension patterns.

## Features

- **A2A Rate Limiting Extension**: Demonstrates proper integration of a reusable A2A extension
- **Token Bucket Algorithm**: Allows burst traffic while maintaining steady-state rate limits
- **Automatic Rate Limiting**: Uses decorator pattern for seamless integration
- **Extension Metadata**: Properly registers extension capabilities in AgentCard
- **Rate Limit Headers**: Includes rate limit information in responses

## Rate Limiting Configuration

This agent is configured with:
- **Algorithm**: Token Bucket with 2x capacity multiplier
- **Default Limits**: 10 requests per minute (configurable via metadata)
- **Key Extraction**: Automatic by client ID, IP address, or user ID
- **Response Headers**: Rate limit status included in all responses

## Getting Started

### 1. Start the Server

```bash
uv run .
```

The agent will start on `http://localhost:9999` with rate limiting active.

### 2. Basic Test Client

```bash
uv run test_client.py
```

### 3. Rate Limiting Test

```bash
uv run rate_limit_test.py
```

This will demonstrate rate limiting by making multiple rapid requests.

## Testing Rate Limiting

### Normal Request
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

### Request with Extension Activation
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
        "role": "user",
        "metadata": {
          "github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1/limits": {
            "requests": 5,
            "window": 60
          }
        }
      }
    }
  }'
```

## Response Format

### Successful Response (Within Rate Limit)
```json
{
  "jsonrpc": "2.0",
  "id": "test",
  "result": {
    "message": {
      "kind": "message",
      "messageId": "msg-response-123",
      "parts": [
        {
          "kind": "text",
          "text": "Hello World"
        }
      ],
      "role": "agent",
      "metadata": {
        "github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1/result": {
          "allowed": true,
          "remaining": 4,
          "limit_type": "token_bucket"
        }
      }
    }
  }
}
```

### Rate Limited Response
```json
{
  "jsonrpc": "2.0",
  "id": "test",
  "result": {
    "message": {
      "kind": "message",
      "messageId": "msg-response-456",
      "parts": [
        {
          "kind": "text",
          "text": "Rate limit exceeded. 0 requests remaining. Retry after 15.3 seconds."
        }
      ],
      "role": "agent"
    }
  }
}
```

## Architecture Overview

### Extension Integration

This example demonstrates the **decorator pattern** for extension integration:

1. **Extension Initialization**: Rate limiting extension with token bucket algorithm
2. **AgentCard Integration**: Extension metadata added to capabilities
3. **Executor Wrapping**: Base executor wrapped with rate limiting logic
4. **Automatic Operation**: Rate limits applied transparently

### Code Structure

```python
# 1. Initialize extension
rate_limiter = RateLimitingExtension(
    limiter=TokenBucketLimiter(capacity_multiplier=2.0)
)

# 2. Add to agent card
public_agent_card = rate_limiter.add_to_card(public_agent_card)

# 3. Wrap executor
base_executor = HelloWorldAgentExecutor() 
rate_limited_executor = rate_limiter.wrap_executor(base_executor)

# 4. Use in request handler
request_handler = DefaultRequestHandler(
    agent_executor=rate_limited_executor,
    task_store=InMemoryTaskStore(),
)
```

## Rate Limiting Behavior

### Token Bucket Algorithm

- **Capacity**: 20 tokens (10 requests × 2.0 multiplier)
- **Refill Rate**: 10 tokens per minute
- **Burst Allowance**: Up to 20 requests initially, then steady 10/minute
- **Key Extraction**: Automatic based on client context

### Extension Activation

The rate limiting extension can be activated in multiple ways:

1. **Always Active**: Via decorator pattern (current implementation)
2. **Header-Based**: Via `X-A2A-Extensions` header
3. **Metadata-Based**: Via message metadata configuration
4. **Manual**: Explicit checks in agent code

## Extension Benefits

### For Developers
- **Zero Code Changes**: Decorator pattern requires no agent logic modifications
- **Flexible Configuration**: Multiple algorithms and parameters
- **A2A Compliant**: Follows official extension specifications
- **Production Ready**: Thread-safe, memory efficient

### For Operators
- **Resource Protection**: Prevents abuse and overload
- **Cost Control**: Manages expensive operations
- **Monitoring**: Built-in rate limit metrics
- **Graceful Degradation**: Informative error responses

## Comparison with Basic HelloWorld

| Aspect | Basic HelloWorld | With Rate Limiting |
|--------|------------------|-------------------|
| **Request Processing** | Unlimited | Rate limited |
| **Resource Usage** | Uncontrolled | Protected |
| **Response Headers** | Basic | Includes rate limit info |
| **Extension Support** | None | Full A2A extension |
| **Production Readiness** | Demo only | Production capable |

## Advanced Configuration

### Custom Rate Limits

To configure different rate limits per client:

```python
def custom_key_extractor(context: RequestContext) -> str:
    # Extract client tier from context
    client_tier = getattr(context, 'client_tier', 'free')
    client_id = getattr(context, 'client_id', 'unknown')
    return f"{client_tier}:{client_id}"

# Different limits per tier
tier_limits = {
    'free': {"requests": 10, "window": 60},
    'premium': {"requests": 100, "window": 60},
    'enterprise': {"requests": 1000, "window": 60}
}

rate_limiter = RateLimitingExtension(
    key_extractor=custom_key_extractor
)
```

### Multiple Algorithms

Combine different rate limiting strategies:

```python
from ratelimiter_ext import CompositeLimiter, TokenBucketLimiter, FixedWindowLimiter

composite = CompositeLimiter({
    "burst": TokenBucketLimiter(),      # Handle traffic bursts
    "sustained": FixedWindowLimiter()   # Long-term rate control
})

rate_limiter = RateLimitingExtension(limiter=composite)
```

## Build Container Image

Agent can also be built using a container file:

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

## Extension Specification

- **Extension URI**: `https://github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1`
- **Limits Metadata**: `github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1/limits`
- **Result Metadata**: `github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1/result`
- **Activation Header**: `X-A2A-Extensions`

## Disclaimer

This sample demonstrates A2A protocol extension patterns and rate limiting concepts. For production use, consider:
- Persistent storage backends (Redis, database)
- Distributed rate limiting across multiple instances  
- Advanced security and authentication
- Monitoring and alerting integration
- Custom rate limiting policies per use case

Important: The sample code provided is for demonstration purposes and illustrates
the mechanics of the Agent-to-Agent (A2A) protocol. When building production
applications, it is critical to treat any agent operating outside of your direct
control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its
AgentCard, messages, artifacts, and task statuses—should be handled as
untrusted input. For example, a malicious agent could provide an AgentCard
containing crafted data in its fields (e.g., description, name,
skills.description). If this data is used without sanitization to construct
prompts for a Large Language Model (LLM), it could expose your application to
prompt injection attacks. Failure to properly validate and sanitize this data
before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.