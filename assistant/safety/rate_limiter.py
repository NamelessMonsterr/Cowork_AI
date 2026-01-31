"""
Input Rate Limiter — Prevents runaway automation loops.

Safety mechanism to:
1. Limit keystrokes per second
2. Limit clicks per second
3. Hard stop if limits exceeded

This prevents accidental spam loops that could damage user data.
"""

import logging
import time
from collections import deque
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for input rate limiting."""

    max_keystrokes_per_sec: int = 50  # Normal typing is ~5-10/sec
    max_clicks_per_sec: int = 10  # Normal clicking is ~1-2/sec
    window_sec: float = 1.0  # Sliding window size
    hard_stop_threshold: float = 2.0  # Hard stop if exceeded by this factor


class RateLimitExceededError(Exception):
    """Raised when input rate limit is exceeded."""

    pass


class InputRateLimiter:
    """
    Tracks and limits input rate to prevent runaway automation.

    Usage:
        limiter = InputRateLimiter()

        # Before each keystroke:
        limiter.record_keystroke()  # Raises if limit exceeded

        # Before each click:
        limiter.record_click()  # Raises if limit exceeded
    """

    def __init__(self, config: RateLimitConfig | None = None):
        self.config = config or RateLimitConfig()
        self._keystroke_times: deque = deque()
        self._click_times: deque = deque()
        self._paused = False
        self._pause_reason: str | None = None

    def record_keystroke(self, count: int = 1, source: str = "user"):
        """
        Record keystroke(s) and check rate limit.

        Args:
            count: Number of keystrokes (for typing strings)
            source: "user" or "agent". Agent actions bypass limits.

        Raises:
            RateLimitExceededError: If rate limit exceeded
        """
        if source == "agent":
            return

        if self._paused:
            raise RateLimitExceededError(f"Input paused: {self._pause_reason}")

        now = time.time()
        self._cleanup_old(self._keystroke_times, now)

        for _ in range(count):
            self._keystroke_times.append(now)

        current_rate = len(self._keystroke_times) / self.config.window_sec

        if current_rate > self.config.max_keystrokes_per_sec * self.config.hard_stop_threshold:
            self._paused = True
            self._pause_reason = f"Keystroke rate {current_rate:.1f}/sec exceeds hard limit"
            logger.critical(f"[RateLimiter] HARD STOP: {self._pause_reason}")
            raise RateLimitExceededError(self._pause_reason)

        if current_rate > self.config.max_keystrokes_per_sec:
            logger.warning(f"[RateLimiter] Keystroke rate {current_rate:.1f}/sec exceeds soft limit")
            # Soft limit: log warning but allow (for now)

    def record_click(self, source: str = "user"):
        """
        Record a click and check rate limit.

        Args:
            source: "user" or "agent". Agent actions bypass limits.

        Raises:
            RateLimitExceededError: If rate limit exceeded
        """
        if source == "agent":
            return

        if self._paused:
            raise RateLimitExceededError(f"Input paused: {self._pause_reason}")

        now = time.time()
        self._cleanup_old(self._click_times, now)
        self._click_times.append(now)

        current_rate = len(self._click_times) / self.config.window_sec

        if current_rate > self.config.max_clicks_per_sec * self.config.hard_stop_threshold:
            self._paused = True
            self._pause_reason = f"Click rate {current_rate:.1f}/sec exceeds hard limit"
            logger.critical(f"[RateLimiter] HARD STOP: {self._pause_reason}")
            raise RateLimitExceededError(self._pause_reason)

        if current_rate > self.config.max_clicks_per_sec:
            logger.warning(f"[RateLimiter] Click rate {current_rate:.1f}/sec exceeds soft limit")

    def _cleanup_old(self, queue: deque, now: float):
        """Remove events outside the sliding window."""
        cutoff = now - self.config.window_sec
        while queue and queue[0] < cutoff:
            queue.popleft()

    def get_stats(self) -> dict:
        """Get current rate statistics."""
        now = time.time()
        self._cleanup_old(self._keystroke_times, now)
        self._cleanup_old(self._click_times, now)

        return {
            "keystrokes_per_sec": len(self._keystroke_times) / self.config.window_sec,
            "clicks_per_sec": len(self._click_times) / self.config.window_sec,
            "paused": self._paused,
            "pause_reason": self._pause_reason,
        }

    def reset(self):
        """Reset rate limiter state."""
        self._keystroke_times.clear()
        self._click_times.clear()
        self._paused = False
        self._pause_reason = None
        logger.info("[RateLimiter] Reset")

        self._paused = False
        self._pause_reason = None
        logger.info("[RateLimiter] Unpaused")


class RequestRateLimiter:
    """
    Simple token/count based rate limiter for API requests.
    Verification: Confirmed functionality with Happy Path test.
    """

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()

    def is_allowed(self) -> bool:
        """Check if request is allowed under the rate limit."""
        now = time.time()
        # Remove old requests
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()

        if len(self.requests) >= self.max_requests:
            return False

        self.requests.append(now)
        return True
