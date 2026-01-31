"""
Selector Cache - Optimizes repeated element lookups.

Caches resolved UISelectors based on action signature and window state.
Part of W7 optimization suite.
"""

import threading
import time

from assistant.ui_contracts.schemas import UISelector


class SelectorCache:
    def __init__(self, ttl_sec: float = 60.0):
        self._cache = {}
        self._lock = threading.Lock()
        self.ttl = ttl_sec

    def get(self, key: str) -> UISelector | None:
        """Retrieve cached selector if valid."""
        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None

            # Check expiry
            if time.time() - entry["ts"] > self.ttl:
                del self._cache[key]
                return None

            return entry["selector"]

    def set(self, key: str, selector: UISelector):
        """Cache a resolved selector."""
        with self._lock:
            self._cache[key] = {"selector": selector, "ts": time.time()}

    def invalidate(self, key: str = None):
        """Invalidate specific key or entire cache."""
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()

    def generate_key(self, tool: str, args: dict, window_title: str) -> str:
        """Generate deterministic cache key."""
        # Normalize args to string
        args_str = str(sorted(args.items()))
        return f"{tool}|{args_str}|{window_title}"
