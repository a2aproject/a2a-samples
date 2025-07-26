# utils.py

import threading

from typing import Any


class InMemoryCache:
    """Simple thread-safe in-memory cache with no expiration."""

    def __init__(self):
        self._lock = threading.Lock()
        self._store: dict[str, Any] = {}

    def get(self, key: str) -> Any | None:
        with self._lock:
            return self._store.get(key)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = value

    def delete(self, key: str) -> None:
        with self._lock:
            if key in self._store:
                del self._store[key]

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# Singleton cache instance for use across modules
cache = InMemoryCache()
