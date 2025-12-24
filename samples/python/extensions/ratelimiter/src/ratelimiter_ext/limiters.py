"""Rate limiting implementation using Token Bucket algorithm.

This module provides a simple, production-ready rate limiting implementation
for A2A agents. For more sophisticated rate limiting needs, consider using
battle-tested libraries like python-limits, slowapi, or similar.
"""

import time
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class RateLimitResult:
    """Result of a rate limit check.

    This data structure is used to communicate rate limit status both
    internally (for enforcement) and externally (via extension metadata).
    """

    allowed: bool
    remaining: int = 0
    reset_time: float | None = None
    retry_after: float | None = None
    limit_type: str = "token_bucket"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for metadata serialization."""
        return {
            "allowed": self.allowed,
            "remaining": self.remaining,
            "reset_time": self.reset_time,
            "retry_after": self.retry_after,
            "limit_type": self.limit_type,
        }


class TokenBucketLimiter:
    """Token bucket rate limiting algorithm.

    This algorithm allows for burst traffic up to bucket capacity while
    maintaining steady-state rate limiting through token refill.

    The token bucket is a good general-purpose algorithm that:
    - Allows controlled bursts of traffic
    - Maintains fair long-term rate limits
    - Is memory efficient (stores only token count per key)
    - Handles variable request rates well

    For production use, consider:
    - Using a distributed rate limiter (Redis-based) for multi-instance deployments
    - Implementing persistent storage for rate limit state
    - Using battle-tested libraries like python-limits or slowapi

    Example:
        limiter = TokenBucketLimiter(capacity_multiplier=2.0)
        result = limiter.check_limit("user:123", limit=60, window=60)
        if result.allowed:
            # Process request
            pass
        else:
            # Return error with result.retry_after
            pass
    """

    def __init__(self, capacity_multiplier: float = 2.0):
        """Initialize token bucket limiter.

        Args:
            capacity_multiplier: How much larger bucket is than rate limit.
                For example, with limit=10 and multiplier=2.0, bucket capacity is 20.
                This allows for burst traffic up to 20 requests before rate limiting.
        """
        self.capacity_multiplier = capacity_multiplier
        self.buckets: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def check_limit(self, key: str, limit: int, window: int) -> RateLimitResult:
        """Check if request should be allowed under current rate limit.

        This method is thread-safe and can be called concurrently.

        Args:
            key: Unique identifier for rate limiting (e.g., "user:123", "ip:1.2.3.4")
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            RateLimitResult with allowed status and metadata
        """
        now = time.time()
        rate = limit / window  # tokens per second
        capacity = int(limit * self.capacity_multiplier)

        with self._lock:
            if key not in self.buckets:
                self.buckets[key] = {
                    "tokens": capacity,
                    "last_update": now,
                }

            bucket = self.buckets[key]

            # Refill tokens based on time elapsed
            time_elapsed = now - bucket["last_update"]
            tokens_to_add = time_elapsed * rate
            bucket["tokens"] = min(capacity, bucket["tokens"] + tokens_to_add)
            bucket["last_update"] = now

            if bucket["tokens"] >= 1:
                # Request allowed - consume one token
                bucket["tokens"] -= 1

                # Calculate when bucket will reach full capacity
                time_to_full = (capacity - bucket["tokens"]) / rate
                reset_time = now + time_to_full if time_to_full > 0 else now

                return RateLimitResult(
                    allowed=True,
                    remaining=int(bucket["tokens"]),
                    reset_time=reset_time,
                    limit_type="token_bucket",
                )
            else:
                # Request denied - calculate retry time
                retry_after = (1 - bucket["tokens"]) / rate

                # Calculate when bucket will have enough tokens for next request
                time_to_full = (capacity - bucket["tokens"]) / rate
                reset_time = now + time_to_full if time_to_full > 0 else now

                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    retry_after=retry_after,
                    reset_time=reset_time,
                    limit_type="token_bucket",
                )

    def reset(self, key: str) -> None:
        """Reset rate limit state for a specific key.

        This is useful for testing or administrative operations.

        Args:
            key: The rate limit key to reset
        """
        with self._lock:
            if key in self.buckets:
                del self.buckets[key]


__all__ = [
    "RateLimitResult",
    "TokenBucketLimiter",
]
