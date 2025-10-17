# Rate Limiting Extension for A2A Protocol

A comprehensive rate limiting extension for A2A protocol agents, providing flexible rate limiting capabilities with multiple algorithms and integration patterns.

## Features

- **Multiple Rate Limiting Algorithms**:
  - Token Bucket: Allows burst traffic while maintaining steady-state limits
  - Sliding Window: Precise time-based rate limiting  
  - Fixed Window: Memory-efficient fixed interval limiting
  - Composite: Combine multiple strategies for complex policies

- **Flexible Integration**: 5 different integration patterns to suit various needs
- **A2A Protocol Compliant**: Full support for extension headers and metadata
- **Client & Server Support**: Works on both sides of A2A communication
- **Configurable Keys**: Rate limit by IP, user ID, client ID, or custom identifiers

## Installation

```bash
pip install ratelimiter-ext
```

Or install from source:
```bash
cd extensions/ratelimiter
pip install -e .
```

## Quick Start

### Option 1: Manual Rate Limiting (Full Control)

```python
from ratelimiter_ext import RateLimitingExtension, TokenBucketLimiter

# Initialize extension with token bucket algorithm
limiter = RateLimitingExtension(
    limiter=TokenBucketLimiter(capacity_multiplier=2.0)
)

# In your agent executor
async def execute(self, context: RequestContext, event_queue: EventQueue):
    # Check rate limits
    limits = {"requests": 60, "window": 60}  # 60 requests per minute
    result = limiter.check_limit(context, limits)
    
    if not result.allowed:
        error_msg = f"Rate limit exceeded. Retry after {result.retry_after}s"
        await event_queue.enqueue_event(new_agent_text_message(error_msg))
        return
    
    # Process request normally
    # ...
```

### Option 2: Automatic Integration (Easiest)

```python
from ratelimiter_ext import RateLimitingExtension

# Initialize extension
rate_limiter = RateLimitingExtension()

# Wrap your agent executor - automatic rate limiting applied
wrapped_executor = rate_limiter.wrap_executor(original_executor)

# Use in your agent
request_handler = DefaultRequestHandler(
    agent_executor=wrapped_executor,
    task_store=InMemoryTaskStore(),
)
```

### Option 3: AgentCard Integration

```python
# Add rate limiting to your agent card
public_agent_card = AgentCard(
    name='My Rate Limited Agent',
    # ... other config
)

# Add extension to capabilities
public_agent_card = rate_limiter.add_to_card(public_agent_card)
```

## Rate Limiting Algorithms

### Token Bucket

Best for allowing burst traffic while maintaining long-term rate limits:

```python
from ratelimiter_ext import TokenBucketLimiter

limiter = RateLimitingExtension(
    limiter=TokenBucketLimiter(capacity_multiplier=2.0)
)
```

**Use cases**: API gateways, user-facing services, bursty workloads

### Sliding Window

Most precise algorithm, maintains exact request counts over time:

```python
from ratelimiter_ext import SlidingWindowLimiter

limiter = RateLimitingExtension(
    limiter=SlidingWindowLimiter(max_entries_per_key=1000)
)
```

**Use cases**: Strict rate limits, billing systems, quota enforcement

### Fixed Window

Memory efficient, resets counters at fixed intervals:

```python
from ratelimiter_ext import FixedWindowLimiter

limiter = RateLimitingExtension(
    limiter=FixedWindowLimiter()
)
```

**Use cases**: Simple rate limiting, high-volume systems, basic quotas

### Composite Limiting

Combine multiple strategies for complex policies:

```python
from ratelimiter_ext import CompositeLimiter, TokenBucketLimiter, FixedWindowLimiter

composite = CompositeLimiter({
    "burst": TokenBucketLimiter(),      # Handle bursts
    "sustained": FixedWindowLimiter()   # Long-term limits
})

limiter = RateLimitingExtension(limiter=composite)
```

**Use cases**: Complex SLAs, tiered service levels, sophisticated policies

## Configuration

### Rate Limit Configuration

Rate limits are configured via message metadata or programmatically:

```python
# Via message metadata (A2A protocol compliant)
limits = {
    "requests": 100,     # Maximum requests
    "window": 60,        # Time window in seconds
}

# Check limits
result = limiter.check_limit(context, limits)
```

### Custom Key Extraction

Customize how rate limit keys are generated:

```python
def custom_key_extractor(context: RequestContext) -> str:
    # Rate limit by API key
    if hasattr(context, 'api_key'):
        return f"api_key:{context.api_key}"
    
    # Fallback to IP
    return f"ip:{context.remote_addr}"

limiter = RateLimitingExtension(
    key_extractor=custom_key_extractor
)
```

### A2A Protocol Integration

The extension follows A2A protocol standards for activation and configuration:

```python
# Extension URI
URI = "https://github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1"

# Activate via X-A2A-Extensions header
headers = {
    "X-A2A-Extensions": URI
}

# Configure via message metadata
message_metadata = {
    "github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1/limits": {
        "requests": 50,
        "window": 60
    }
}
```

## Client-Side Usage

### Client Interceptor

Automatically add rate limiting headers to outgoing requests:

```python
# Create client with rate limiting
client_factory = rate_limiter.wrap_client_factory(original_factory)
client = client_factory.create(agent_card)

# All requests will include rate limiting headers
response = await client.send_message(message)
```

### Manual Client Integration

```python
# Wrap existing client
rate_limited_client = rate_limiter.wrap_client(original_client)

# Use normally - rate limiting handled automatically
async for event in rate_limited_client.send_message(message):
    print(event)
```

## Integration Patterns

Following the timestamp extension patterns, this extension provides 5 integration options:

### 1. Self-Serve (Manual Control)
```python
result = limiter.check_limit(context, limits)
if not result.allowed:
    # Handle rate limit exceeded
```

### 2. Helper Classes
```python
helper = limiter.get_rate_limiter(context)
result = helper.enforce_limit(limits)  # Raises exception if exceeded
```

### 3. Context Manager
```python
with limiter.get_rate_limiter(context) as rate_limit:
    result = rate_limit.check_limit(limits)
    # Handle result
```

### 4. Event Integration
```python
# Automatically add rate limit headers to all responses
limiter.add_rate_limit_headers(result, response_message)
```

### 5. Full Decoration (Recommended)
```python
# Complete hands-off integration
executor = limiter.wrap_executor(original_executor)
```

## Response Headers

When rate limiting is active, responses include metadata with limit information:

```json
{
  "metadata": {
    "github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1/result": {
      "allowed": true,
      "remaining": 45,
      "reset_time": 1640995260.0,
      "limit_type": "token_bucket"
    }
  }
}
```

## Error Handling

### Rate Limit Exceeded

When limits are exceeded, the extension provides detailed information:

```python
try:
    result = limiter.check_and_enforce(context, limits)
except RateLimitExceeded as e:
    print(f"Rate limit exceeded: {e}")
    print(f"Retry after: {e.result.retry_after} seconds")
    print(f"Remaining requests: {e.result.remaining}")
```

### Automatic Error Responses

When using the decorator pattern, rate limit exceeded responses are sent automatically:

```text
"Rate limit exceeded. 0 requests remaining. Retry after 15.3 seconds."
```

## Advanced Usage

### Custom Rate Limiter

Implement your own rate limiting algorithm:

```python
from ratelimiter_ext import RateLimiter, RateLimitResult

class CustomLimiter(RateLimiter):
    def check_limit(self, key: str, limit: int, window: int) -> RateLimitResult:
        # Your custom logic here
        return RateLimitResult(allowed=True, remaining=limit)
    
    def reset(self, key: str) -> None:
        # Reset state for key
        pass

# Use custom limiter
limiter = RateLimitingExtension(limiter=CustomLimiter())
```

### Persistent Storage

For production use, implement persistent storage backends:

```python
import redis

class RedisTokenBucketLimiter(RateLimiter):
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def check_limit(self, key: str, limit: int, window: int) -> RateLimitResult:
        # Implement Redis-based token bucket
        # ...
```

### Multi-Tier Rate Limiting

Implement different limits for different user tiers:

```python
def tier_based_key_extractor(context: RequestContext) -> str:
    user_tier = getattr(context, 'user_tier', 'free')
    user_id = getattr(context, 'user_id', 'anonymous')
    return f"{user_tier}:{user_id}"

def get_limits_for_tier(context: RequestContext) -> dict:
    user_tier = getattr(context, 'user_tier', 'free')
    
    tier_limits = {
        'free': {"requests": 10, "window": 60},
        'premium': {"requests": 100, "window": 60}, 
        'enterprise': {"requests": 1000, "window": 60}
    }
    
    return tier_limits.get(user_tier, tier_limits['free'])

# Usage
limiter = RateLimitingExtension(
    key_extractor=tier_based_key_extractor
)

limits = get_limits_for_tier(context)
result = limiter.check_limit(context, limits)
```

## Extension URI

This extension follows A2A protocol standards:

- **Extension URI**: `https://github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1`
- **Limits Metadata Field**: `github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1/limits`
- **Result Metadata Field**: `github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1/result`

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please see the main A2A samples repository for contribution guidelines.