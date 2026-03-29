# Rate Limiting Usage Signals Extension for A2A Protocol

An A2A protocol extension that defines a standard way for agents to communicate rate limiting information to clients.

> **📁 Location**: `samples/python/extensions/ratelimiter/`
>
> **🚀 Want to see it in action?** Check out the full working demo: [HelloWorld with Rate Limiting](../../agents/helloworld_with_ratelimiter/) (`samples/python/agents/helloworld_with_ratelimiter/`)

## Purpose

**This extension does NOT enforce rate limits.** Agents should implement rate limiting independently to protect their resources. This extension provides a communication protocol for sharing usage data (remaining quota, retry timing, etc.) with clients.

### Key Concepts

- **Rate limiting enforcement**: Agent's responsibility (always active, independent of extension)
- **Extension purpose**: Communication of usage signals to clients
- **Extension activation**: Client signals "I understand rate limit data, please include it"

Think of this extension like a dashboard - it doesn't control the car's speed, it just shows you how fast you're going.

## Why This Matters

Agents will enforce rate limits whether clients want them to or not - that's resource protection. But without this extension, clients are blind to their usage:

- ❌ **Without extension**: Client gets "Rate limit exceeded" and must guess when to retry
- ✅ **With extension**: Client sees "45 requests remaining, retry after 15.3s" and can act intelligently

## Quick Start

### Agent Side (3 steps)

```python
from ratelimiter_ext import RateLimitingExtension, TokenBucketLimiter

# 1. Initialize limiter and extension
self.rate_limiter = TokenBucketLimiter(capacity_multiplier=2.0)
self.rate_limit_ext = RateLimitingExtension()

# 2. Check rate limit
usage = self.rate_limiter.check_limit(key="user:123", limit=10, window=60)

# 3. Add usage signals if client requested them
if self.rate_limit_ext.is_activated(context):
    self.rate_limit_ext.add_usage_signals(message, usage)
```

See [examples/basic_usage.py](examples/basic_usage.py) for a complete implementation.

### Advertise Extension in AgentCard

```python
from ratelimiter_ext import RateLimitingExtension

rate_limit_ext = RateLimitingExtension()
agent_card = rate_limit_ext.add_to_card(agent_card)
```

### Client Side: Requesting Usage Signals

Include the extension URI in the `X-A2A-Extensions` header:

```text
X-A2A-Extensions: https://github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1
```

## Response Format

When the extension is activated, responses include usage signals in metadata:

```json
{
  "message": {
    "kind": "message",
    "parts": [{"kind": "text", "text": "Hello World"}],
    "role": "agent",
    "metadata": {
      "github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1/result": {
        "allowed": true,
        "remaining": 45,
        "reset_time": 1640995260.0,
        "retry_after": 15.3,
        "limit_type": "token_bucket"
      }
    }
  }
}
```

## Rate Limiting Implementation

### Included Token Bucket Limiter

```python
from ratelimiter_ext import TokenBucketLimiter

limiter = TokenBucketLimiter(capacity_multiplier=2.0)
result = limiter.check_limit("user:123", limit=60, window=60)
```

- **Pros**: Simple, no dependencies, good for examples
- **Cons**: In-memory only, not distributed

### Production Libraries

For real-world deployments, use battle-tested libraries like:
- `python-limits`: Flexible, multiple backends (Redis, Memcache, etc.)
- `slowapi`: FastAPI integration
- `flask-limiter`: Flask integration

See [examples/production_patterns.py](examples/production_patterns.py) for advanced patterns including:
- Different limits per user tier
- Client identity extraction from OAuth/API keys
- Redis-backed distributed rate limiting
- Graceful degradation

## Extension Specification

### Extension URI
```text
https://github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1
```

### Metadata Schema

**Field name**: `github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1/result`

```typescript
{
  allowed: boolean;        // Was request allowed?
  remaining: number;       // Requests remaining in quota
  reset_time?: number;     // Unix timestamp when quota resets
  retry_after?: number;    // Seconds to wait before retry (if denied)
  limit_type: string;      // Algorithm used (e.g., "token_bucket")
}
```

## Design Philosophy

This extension follows A2A protocol principles:

1. **Extensions are about data, not behavior**
    - Extension = communication protocol
    - Behavior (enforcement) = agent's responsibility

2. **Optional client participation**
    - Agents enforce limits regardless
    - Extension gives clients visibility
    - Clients choose whether to receive signals

3. **Server-driven policies**
    - Server determines rate limits (not client)
    - Server extracts client identity (OAuth, API keys, etc.)
    - Client cannot dictate their own limits

## Examples

### Code Patterns (Copy & Adapt)
- **Basic Implementation**: [examples/basic_usage.py](examples/basic_usage.py) - Complete agent executor pattern
- **Production Patterns**: [examples/production_patterns.py](examples/production_patterns.py) - OAuth, Redis, tiered limits, etc.

### Runnable Demo (Run & Test)
- **HelloWorld with Rate Limiting**: [samples/python/agents/helloworld_with_ratelimiter/](../../agents/helloworld_with_ratelimiter/) - Full working agent server with test scripts

Start the demo:
```bash
cd samples/python/agents/helloworld_with_ratelimiter
uv run .
```

## Production Considerations

1. **Distributed Systems**: Use Redis or similar for shared state across instances
2. **Persistent Storage**: Survive restarts with persistent backends
3. **Monitoring**: Track rate limit hits, denials, and usage patterns
4. **Security**: Validate client identity with OAuth/API keys, not IP addresses
5. **Graceful Failures**: Allow requests if rate limiter is unavailable
6. **Audit Logging**: Log rate limit violations for security monitoring

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please see the main A2A samples repository for contribution guidelines.
