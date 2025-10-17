"""Rate limiting algorithms implementation.

This module provides various rate limiting strategies that can be used
independently or combined for flexible rate limiting policies.
"""

import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    remaining: int = 0
    reset_time: float | None = None
    retry_after: float | None = None
    limit_type: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for metadata."""
        return {
            "allowed": self.allowed,
            "remaining": self.remaining,
            "reset_time": self.reset_time,
            "retry_after": self.retry_after,
            "limit_type": self.limit_type,
        }


class RateLimiter(ABC):
    """Abstract base class for rate limiting algorithms."""

    @abstractmethod
    def check_limit(self, key: str, limit: int, window: int) -> RateLimitResult:
        """Check if request should be allowed under rate limit.

        Args:
            key: Unique identifier for the rate limit (e.g., user_id, ip_address)
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            RateLimitResult indicating if request is allowed
        """
        pass

    @abstractmethod
    def reset(self, key: str) -> None:
        """Reset rate limit state for a specific key."""
        pass


class TokenBucketLimiter(RateLimiter):
    """Token bucket rate limiting algorithm.

    Allows for burst traffic up to bucket capacity while maintaining
    steady-state rate limiting through token refill.
    """

    def __init__(self, capacity_multiplier: float = 2.0):
        """Initialize token bucket limiter.

        Args:
            capacity_multiplier: How much larger bucket is than rate limit
        """
        self.capacity_multiplier = capacity_multiplier
        self.buckets: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def check_limit(self, key: str, limit: int, window: int) -> RateLimitResult:
        """Check token bucket for request allowance."""
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
                bucket["tokens"] -= 1
                return RateLimitResult(
                    allowed=True,
                    remaining=int(bucket["tokens"]),
                    limit_type="token_bucket",
                )
            else:
                retry_after = (1 - bucket["tokens"]) / rate
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    retry_after=retry_after,
                    limit_type="token_bucket",
                )

    def reset(self, key: str) -> None:
        """Reset token bucket for key."""
        with self._lock:
            if key in self.buckets:
                del self.buckets[key]


class SlidingWindowLimiter(RateLimiter):
    """Sliding window rate limiting algorithm.

    Maintains a precise sliding window of request timestamps
    for accurate rate limiting.
    """

    def __init__(self, max_entries_per_key: int = 10000):
        """Initialize sliding window limiter.

        Args:
            max_entries_per_key: Maximum timestamps to track per key
        """
        self.max_entries_per_key = max_entries_per_key
        self.windows: dict[str, deque] = {}
        self._lock = Lock()

    def check_limit(self, key: str, limit: int, window: int) -> RateLimitResult:
        """Check sliding window for request allowance."""
        now = time.time()
        window_start = now - window

        with self._lock:
            if key not in self.windows:
                self.windows[key] = deque()

            request_times = self.windows[key]

            # Remove expired entries
            while request_times and request_times[0] <= window_start:
                request_times.popleft()

            current_count = len(request_times)

            if current_count < limit:
                request_times.append(now)
                # Prevent memory buildup
                if len(request_times) > self.max_entries_per_key:
                    request_times.popleft()

                return RateLimitResult(
                    allowed=True,
                    remaining=limit - current_count - 1,
                    reset_time=now + window,
                    limit_type="sliding_window",
                )
            else:
                # Calculate retry after based on oldest entry
                oldest_in_window = request_times[0]
                retry_after = oldest_in_window + window - now + 0.001  # Small buffer

                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    retry_after=max(0, retry_after),
                    reset_time=oldest_in_window + window,
                    limit_type="sliding_window",
                )

    def reset(self, key: str) -> None:
        """Reset sliding window for key."""
        with self._lock:
            if key in self.windows:
                self.windows[key].clear()


class FixedWindowLimiter(RateLimiter):
    """Fixed window rate limiting algorithm.

    Simple algorithm that resets counters at fixed intervals.
    Less precise than sliding window but more memory efficient.
    """

    def __init__(self):
        """Initialize fixed window limiter."""
        self.windows: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def check_limit(self, key: str, limit: int, window: int) -> RateLimitResult:
        """Check fixed window for request allowance."""
        now = time.time()
        window_start = int(now // window) * window

        with self._lock:
            if key not in self.windows:
                self.windows[key] = {
                    "count": 0,
                    "window_start": window_start,
                }

            window_data = self.windows[key]

            # Reset window if expired
            if window_data["window_start"] != window_start:
                window_data["count"] = 0
                window_data["window_start"] = window_start

            if window_data["count"] < limit:
                window_data["count"] += 1
                return RateLimitResult(
                    allowed=True,
                    remaining=limit - window_data["count"],
                    reset_time=window_start + window,
                    limit_type="fixed_window",
                )
            else:
                retry_after = window_start + window - now
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    retry_after=max(0, retry_after),
                    reset_time=window_start + window,
                    limit_type="fixed_window",
                )

    def reset(self, key: str) -> None:
        """Reset fixed window for key."""
        with self._lock:
            if key in self.windows:
                del self.windows[key]


class CompositeLimiter(RateLimiter):
    """Composite limiter that combines multiple strategies.

    All limiters must allow the request for it to be permitted.
    Useful for implementing complex policies like burst + sustained rates.
    """

    def __init__(self, limiters: dict[str, RateLimiter]):
        """Initialize composite limiter.

        Args:
            limiters: Dictionary of named limiters to combine
        """
        self.limiters = limiters

    def check_limit(self, key: str, limit: int, window: int) -> RateLimitResult:
        """Check all limiters - request must pass all to be allowed."""
        results = []

        for _name, limiter in self.limiters.items():
            result = limiter.check_limit(key, limit, window)
            results.append(result)

            if not result.allowed:
                # Return the most restrictive result
                result.limit_type = f"composite_{result.limit_type}"
                return result

        # All limiters allowed the request
        min_remaining = min(r.remaining for r in results if r.remaining is not None)
        return RateLimitResult(
            allowed=True,
            remaining=min_remaining if min_remaining is not None else 0,
            limit_type="composite",
        )

    def reset(self, key: str) -> None:
        """Reset all component limiters."""
        for limiter in self.limiters.values():
            limiter.reset(key)


__all__ = [
    "CompositeLimiter",
    "FixedWindowLimiter",
    "RateLimitResult",
    "RateLimiter",
    "SlidingWindowLimiter",
    "TokenBucketLimiter",
]
