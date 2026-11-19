"""TTL-based in-memory and disk cache for API queries and geocoding."""

import time
import threading
from typing import Any, Optional, Dict, Tuple


class SimpleTTLCache:
    """Thread-safe in-memory cache with time-to-live expiration."""

    def __init__(self, default_ttl_seconds: int = 3600):
        self._default_ttl = default_ttl_seconds
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve item if present and not expired."""
        with self._lock:
            if key not in self._cache:
                return None
            val, expiry = self._cache[key]
            if time.time() > expiry:
                del self._cache[key]
                return None
            return val

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store item with explicit or default TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expiry = time.time() + ttl
        with self._lock:
            self._cache[key] = (value, expiry)

    def has(self, key: str) -> bool:
        """Check if valid unexpired key exists."""
        return self.get(key) is not None

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired keys and return count of deleted items."""
        now = time.time()
        removed = 0
        with self._lock:
            keys_to_delete = [k for k, (_, exp) in self._cache.items() if now > exp]
            for k in keys_to_delete:
                del self._cache[k]
                removed += 1
        return removed
