"""
Selector Cache - Memory for UI element locations.

Caches found elements to speed up repeated actions:
- Last element bounding boxes
- Last clicked element selectors
- Last known window handles

This makes the agent faster and more stable by avoiding
repeated UI tree traversals or OCR scans.
"""

import time
import threading
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from collections import OrderedDict

from assistant.ui_contracts.schemas import UISelector


@dataclass
class CacheEntry:
    """A cached selector with metadata."""
    selector: UISelector
    step_id: str
    tool: str
    created_at: float
    last_used_at: float
    hit_count: int = 0
    valid: bool = True


class SelectorCache:
    """
    LRU cache for UI selectors.
    
    Features:
    - Automatic expiry (default 5 minutes)
    - LRU eviction when full
    - Validation hooks
    - Statistics tracking
    
    Usage:
        cache = SelectorCache(max_size=100, ttl_sec=300)
        
        # After finding element:
        cache.put("step_1", selector)
        
        # Before action:
        selector = cache.get("step_1")
        if selector:
            # Use cached selector
        else:
            # Find element again
    """

    def __init__(
        self,
        max_size: int = 100,
        ttl_sec: int = 300,  # 5 minutes
    ):
        """
        Initialize SelectorCache.
        
        Args:
            max_size: Maximum number of entries
            ttl_sec: Time-to-live in seconds
        """
        self._max_size = max_size
        self._ttl_sec = ttl_sec
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        
        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }
        
        # Last action context
        self._last_click: Optional[CacheEntry] = None
        self._last_window_hwnd: Optional[int] = None
        self._last_window_title: Optional[str] = None

    def get(self, key: str) -> Optional[UISelector]:
        """
        Get cached selector by key.
        
        Args:
            key: Cache key (usually step_id or a descriptive key)
            
        Returns:
            UISelector if found and valid, None otherwise
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats["misses"] += 1
                return None
            
            # Check expiry
            if self._is_expired(entry):
                self._cache.pop(key)
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                return None
            
            # Check validity
            if not entry.valid:
                self._stats["misses"] += 1
                return None
            
            # Update LRU order
            self._cache.move_to_end(key)
            entry.last_used_at = time.time()
            entry.hit_count += 1
            self._stats["hits"] += 1
            
            return entry.selector

    def put(
        self,
        key: str,
        selector: UISelector,
        step_id: str = "",
        tool: str = "",
    ) -> None:
        """
        Store a selector in cache.
        
        Args:
            key: Cache key
            selector: The selector to cache
            step_id: Associated step ID
            tool: Tool that used this selector
        """
        with self._lock:
            now = time.time()
            
            # Update selector timestamp
            selector.last_validated_at = now
            
            entry = CacheEntry(
                selector=selector,
                step_id=step_id,
                tool=tool,
                created_at=now,
                last_used_at=now,
            )
            
            # Remove old entry if exists
            if key in self._cache:
                self._cache.pop(key)
            
            # Evict if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)  # Remove oldest
                self._stats["evictions"] += 1
            
            self._cache[key] = entry
            
            # Track as last click if it's a click-related tool
            if tool in ("click", "double_click", "right_click"):
                self._last_click = entry

    def invalidate(self, key: str) -> None:
        """Mark a cache entry as invalid."""
        with self._lock:
            if key in self._cache:
                self._cache[key].valid = False

    def invalidate_by_window(self, window_title: str) -> int:
        """
        Invalidate all entries related to a window.
        
        Args:
            window_title: Window title (partial match)
            
        Returns:
            Number of entries invalidated
        """
        count = 0
        title_lower = window_title.lower()
        
        with self._lock:
            for entry in self._cache.values():
                if entry.selector.window_title:
                    if title_lower in entry.selector.window_title.lower():
                        entry.valid = False
                        count += 1
        
        return count

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._last_click = None

    def get_last_click(self) -> Optional[UISelector]:
        """Get the selector from the last click action."""
        with self._lock:
            if self._last_click and self._last_click.valid:
                if not self._is_expired(self._last_click):
                    return self._last_click.selector
        return None

    def set_window_context(self, hwnd: int, title: str) -> None:
        """Update the current window context."""
        with self._lock:
            self._last_window_hwnd = hwnd
            self._last_window_title = title

    def get_window_context(self) -> tuple[Optional[int], Optional[str]]:
        """Get the current window context."""
        with self._lock:
            return self._last_window_hwnd, self._last_window_title

    def get_stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total if total > 0 else 0
            
            return {
                **self._stats,
                "size": len(self._cache),
                "max_size": self._max_size,
                "hit_rate": round(hit_rate, 3),
            }

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if an entry has expired."""
        return (time.time() - entry.created_at) > self._ttl_sec

    def get_all_for_window(self, window_title: str) -> List[UISelector]:
        """
        Get all cached selectors for a window.
        
        Args:
            window_title: Window title (partial match)
            
        Returns:
            List of matching selectors
        """
        results = []
        title_lower = window_title.lower()
        
        with self._lock:
            for entry in self._cache.values():
                if entry.valid and not self._is_expired(entry):
                    if entry.selector.window_title:
                        if title_lower in entry.selector.window_title.lower():
                            results.append(entry.selector)
        
        return results
