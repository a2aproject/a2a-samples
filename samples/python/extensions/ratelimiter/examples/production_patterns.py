"""
Production Patterns: Advanced Rate Limiting Examples

This file demonstrates production-ready patterns for rate limiting in A2A agents:
1. Different limits per user tier
2. Client identity extraction from OAuth/API keys
3. Redis-backed distributed rate limiting
4. Graceful degradation
"""

import logging
from typing import Dict

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message
from ratelimiter_ext import RateLimitingExtension, RateLimitResult

# Optional: Import production rate limiting library
# Uncomment if using python-limits for production
# from limits import RateLimitItemPerSecond
# from limits.storage import RedisStorage
# from limits.strategies import MovingWindowRateLimiter


# ============================================================================
# Pattern 1: Different Limits per User Tier
# ============================================================================


class TieredRateLimitExecutor(AgentExecutor):
    """Agent with different rate limits based on user tier."""

    def __init__(self):
        from ratelimiter_ext import TokenBucketLimiter

        self.rate_limiter = TokenBucketLimiter(capacity_multiplier=2.0)
        self.rate_limit_ext = RateLimitingExtension()

    def _extract_user_tier(self, context: RequestContext) -> str:
        """Extract user tier from authentication context.

        In production, this would come from:
        - OAuth token claims
        - API key lookup in database
        - Session data
        """
        # Example: Parse from OAuth token
        # token = self._verify_oauth_token(context)
        # return token.get('tier', 'free')

        # Placeholder for example
        return "free"

    def get_client_limits(self, context: RequestContext) -> Dict[str, int]:
        """Get rate limits based on user's tier."""
        tier = self._extract_user_tier(context)

        limits = {
            "free": {"limit": 10, "window": 60},  # 10 req/min
            "premium": {"limit": 100, "window": 60},  # 100 req/min
            "enterprise": {"limit": 1000, "window": 60},  # 1000 req/min
        }

        return limits.get(tier, limits["free"])

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        """Execute with tiered rate limiting."""
        client_key = self._get_client_key(context)
        limits = self.get_client_limits(context)

        usage = self.rate_limiter.check_limit(key=client_key, limit=limits["limit"], window=limits["window"])

        if not usage.allowed:
            message = new_agent_text_message(
                f"Rate limit exceeded for your tier. Retry after {usage.retry_after:.1f}s."
            )
            if self.rate_limit_ext.is_activated(context):
                self.rate_limit_ext.add_usage_signals(message, usage)
            await event_queue.enqueue_event(message)
            return

        # Process request...
        result = "Request processed"
        message = new_agent_text_message(result)
        if self.rate_limit_ext.is_activated(context):
            self.rate_limit_ext.add_usage_signals(message, usage)
        await event_queue.enqueue_event(message)

    def _get_client_key(self, context: RequestContext) -> str:
        """Extract client identifier."""
        return f"ip:{getattr(context, 'remote_addr', 'unknown')}"


# ============================================================================
# Pattern 2: Client Identity Extraction (OAuth/API Keys)
# ============================================================================


class SecureIdentityExtractor(AgentExecutor):
    """Agent with secure client identity extraction."""

    def _get_client_key(self, context: RequestContext) -> str:
        """Extract client identifier from auth context.

        Priority:
        1. OAuth token (most secure)
        2. API key (good for service-to-service)
        3. IP address (fallback, not recommended for production)
        """

        # Option 1: Extract from OAuth token
        auth_header = getattr(context, "authorization", None)
        if auth_header and auth_header.startswith("Bearer "):
            token = self._verify_oauth_token(auth_header)
            if token:
                return f"user:{token.get('user_id', 'unknown')}"

        # Option 2: Extract from API key
        api_key = getattr(context, "x_api_key", None)
        if api_key:
            # Verify API key and get associated client ID
            client_id = self._verify_api_key(api_key)
            if client_id:
                return f"api_key:{client_id}"

        # Option 3: Fallback to IP address (not recommended for production)
        # Consider blocking or using very restrictive limits for unidentified clients
        remote_addr = getattr(context, "remote_addr", "unknown")
        logging.warning(f"Unidentified client from {remote_addr}, using IP-based rate limit")
        return f"ip:{remote_addr}"

    def _verify_oauth_token(self, auth_header: str) -> dict:
        """Verify OAuth token and return claims.

        In production, use a library like:
        - python-jose for JWT verification
        - authlib for OAuth client
        """
        # Placeholder - implement actual token verification
        # from jose import jwt
        # token = auth_header.replace('Bearer ', '')
        # return jwt.decode(token, SECRET_KEY, algorithms=['RS256'])
        return {}

    def _verify_api_key(self, api_key: str) -> str:
        """Verify API key and return client ID.

        In production:
        - Look up API key in database
        - Check if key is active/not expired
        - Return associated client/account ID
        """
        # Placeholder - implement actual API key verification
        return None


# ============================================================================
# Pattern 3: Redis-Backed Distributed Rate Limiting
# ============================================================================


class DistributedRateLimitExecutor(AgentExecutor):
    """Agent with Redis-backed distributed rate limiting.

    Use this pattern when running multiple agent instances that need to
    share rate limit state.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """Initialize with Redis storage.

        Requires: pip install limits redis
        """
        # Uncomment for production use:
        # from limits import RateLimitItemPerSecond
        # from limits.storage import RedisStorage
        # from limits.strategies import MovingWindowRateLimiter
        #
        # storage = RedisStorage(redis_url)
        # self.limiter = MovingWindowRateLimiter(storage)
        # self.rate_limit = RateLimitItemPerSecond(10, 1)  # 10 per second

        self.rate_limit_ext = RateLimitingExtension()

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        """Execute with distributed rate limiting."""
        # Check rate limit using python-limits library
        # Uncomment for production use:
        # client_key = self._get_client_key(context)
        # if not self.limiter.hit(self.rate_limit, client_key):
        #     # Rate limited
        #     message = new_agent_text_message("Rate limit exceeded")
        #     await event_queue.enqueue_event(message)
        #     return

        # Process request...
        pass

    def _get_client_key(self, context: RequestContext) -> str:
        """Extract client identifier."""
        return f"ip:{getattr(context, 'remote_addr', 'unknown')}"


# ============================================================================
# Pattern 4: Graceful Degradation
# ============================================================================


class GracefulDegradationExecutor(AgentExecutor):
    """Agent with graceful degradation if rate limiter fails.

    Philosophy: Better to allow requests than block everything if rate
    limiter is unavailable (Redis down, etc.)
    """

    def __init__(self):
        from ratelimiter_ext import TokenBucketLimiter

        self.rate_limiter = TokenBucketLimiter(capacity_multiplier=2.0)
        self.rate_limit_ext = RateLimitingExtension()
        self.logger = logging.getLogger(__name__)

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        """Execute with graceful degradation."""
        client_key = self._get_client_key(context)

        # Try to check rate limit, but don't fail if limiter is unavailable
        try:
            usage = self.rate_limiter.check_limit(key=client_key, limit=10, window=60)
        except Exception as e:
            # Log error but allow request to proceed
            self.logger.error(f"Rate limiter error: {e}", exc_info=True)

            # Create a permissive usage result
            usage = RateLimitResult(allowed=True, remaining=0, limit_type="degraded")

            # Optionally: Track degraded mode for monitoring
            self.logger.warning(f"Rate limiter in degraded mode for client {client_key}")

        # Continue with normal flow
        if not usage.allowed:
            message = new_agent_text_message(f"Rate limit exceeded. Retry after {usage.retry_after:.1f}s.")
            if self.rate_limit_ext.is_activated(context):
                self.rate_limit_ext.add_usage_signals(message, usage)
            await event_queue.enqueue_event(message)
            return

        # Process request...
        result = "Request processed"
        message = new_agent_text_message(result)
        if self.rate_limit_ext.is_activated(context):
            self.rate_limit_ext.add_usage_signals(message, usage)
        await event_queue.enqueue_event(message)

    def _get_client_key(self, context: RequestContext) -> str:
        """Extract client identifier."""
        return f"ip:{getattr(context, 'remote_addr', 'unknown')}"


# ============================================================================
# Pattern 5: Multiple Rate Limit Windows
# ============================================================================


class MultiWindowRateLimitExecutor(AgentExecutor):
    """Agent with multiple rate limit windows (per-second, per-minute, per-hour)."""

    def __init__(self):
        from ratelimiter_ext import TokenBucketLimiter

        self.rate_limiter = TokenBucketLimiter(capacity_multiplier=2.0)
        self.rate_limit_ext = RateLimitingExtension()

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        """Execute with multiple rate limit windows."""
        client_key = self._get_client_key(context)

        # Check multiple rate limit windows
        limits = [
            (10, 1),  # 10 per second
            (100, 60),  # 100 per minute
            (1000, 3600),  # 1000 per hour
        ]

        for limit, window in limits:
            usage = self.rate_limiter.check_limit(key=f"{client_key}:{window}", limit=limit, window=window)

            if not usage.allowed:
                window_name = f"{window}s" if window < 60 else f"{window // 60}m"
                message = new_agent_text_message(
                    f"Rate limit exceeded ({limit}/{window_name}). Retry after {usage.retry_after:.1f}s."
                )
                if self.rate_limit_ext.is_activated(context):
                    self.rate_limit_ext.add_usage_signals(message, usage)
                await event_queue.enqueue_event(message)
                return

        # All rate limits passed, process request...
        result = "Request processed"
        message = new_agent_text_message(result)
        await event_queue.enqueue_event(message)

    def _get_client_key(self, context: RequestContext) -> str:
        """Extract client identifier."""
        return f"ip:{getattr(context, 'remote_addr', 'unknown')}"


# ============================================================================
# Summary
# ============================================================================

"""
Production Deployment Checklist:

1. ✓ Use secure client identification (OAuth tokens, API keys)
2. ✓ Implement tiered rate limits based on subscription/plan
3. ✓ Use distributed rate limiting (Redis) for multi-instance deployments
4. ✓ Add graceful degradation to prevent total service outage
5. ✓ Log rate limit violations for security monitoring
6. ✓ Monitor rate limit hit rates and adjust limits accordingly
7. ✓ Use persistent storage (Redis) to survive restarts
8. ✓ Consider multiple time windows (second, minute, hour, day)
9. ✓ Add metrics/observability for rate limit performance
10. ✓ Document rate limits in your API documentation

Recommended Libraries:
- python-limits: Feature-rich, supports multiple backends
- slowapi: FastAPI integration with clean decorators
- flask-limiter: Flask integration
- redis-py: Direct Redis integration for custom implementations
"""
