"""
Focus Guard — Ensures actions execute in the expected window context.

During execution:
1. Before each action, check if active window matches expected target
2. If focus lost, attempt to refocus
3. If refocus fails, escalate to takeover

This prevents typing/clicking into wrong applications (dangerous).
"""

import logging
import time
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FocusCheckResult:
    """Result of a focus check."""

    is_focused: bool
    expected_title: Optional[str]
    actual_title: Optional[str]
    refocused: bool = False
    error: Optional[str] = None


class FocusGuard:
    """
    Monitors and enforces window focus during automation.

    Usage:
        guard = FocusGuard(computer)
        guard.set_expected_window("Notepad")

        # Before each action:
        result = guard.check_focus()
        if not result.is_focused:
            raise FocusLostError(result.actual_title)
    """

    def __init__(self, computer, max_refocus_attempts: int = 2):
        """
        Args:
            computer: WindowsComputer instance for window detection
            max_refocus_attempts: How many times to try refocusing before fail
        """
        self.computer = computer
        self.max_refocus_attempts = max_refocus_attempts
        self._expected_title: Optional[str] = None
        self._expected_handle: Optional[int] = None

    def set_expected_window(self, title_contains: str, handle: Optional[int] = None):
        """Set the expected window for subsequent actions."""
        self._expected_title = title_contains.lower() if title_contains else None
        self._expected_handle = handle
        logger.info(f"[FocusGuard] Expected window: '{title_contains}'")

    def clear_expectation(self):
        """Clear expected window (allow any)."""
        self._expected_title = None
        self._expected_handle = None

    def check_focus(self, auto_refocus: bool = True) -> FocusCheckResult:
        """
        Check if current focus matches expected window.

        Args:
            auto_refocus: If True, attempt to refocus if focus is lost

        Returns:
            FocusCheckResult with focus status
        """
        if not self._expected_title:
            # No expectation set, always pass
            return FocusCheckResult(
                is_focused=True, expected_title=None, actual_title=None
            )

        active = self.computer.get_active_window()
        if not active:
            return FocusCheckResult(
                is_focused=False,
                expected_title=self._expected_title,
                actual_title=None,
                error="No active window detected",
            )

        actual_title = active.title.lower() if active.title else ""

        # Check by handle first (most reliable)
        if self._expected_handle and active.handle == self._expected_handle:
            return FocusCheckResult(
                is_focused=True,
                expected_title=self._expected_title,
                actual_title=active.title,
            )

        # Check by title contains
        if self._expected_title in actual_title:
            return FocusCheckResult(
                is_focused=True,
                expected_title=self._expected_title,
                actual_title=active.title,
            )

        # Focus lost!
        logger.warning(
            f"[FocusGuard] Focus LOST! Expected '{self._expected_title}', got '{active.title}'"
        )

        if auto_refocus:
            refocused = self._attempt_refocus()
            if refocused:
                return FocusCheckResult(
                    is_focused=True,
                    expected_title=self._expected_title,
                    actual_title=self._get_active_title(),
                    refocused=True,
                )

        return FocusCheckResult(
            is_focused=False,
            expected_title=self._expected_title,
            actual_title=active.title,
            error=f"Focus lost: expected '{self._expected_title}', got '{active.title}'",
        )

    def _attempt_refocus(self) -> bool:
        """Try to refocus the expected window."""
        for attempt in range(self.max_refocus_attempts):
            logger.info(
                f"[FocusGuard] Refocus attempt {attempt + 1}/{self.max_refocus_attempts}"
            )

            try:
                # Use pywinauto to find and focus the window
                from pywinauto import Desktop

                desktop = Desktop(backend="uia")
                windows = desktop.windows(title_re=f".*{self._expected_title}.*")

                if windows:
                    windows[0].set_focus()
                    time.sleep(0.3)  # Wait for focus to settle

                    # Verify refocus worked
                    active = self.computer.get_active_window()
                    if active and self._expected_title in active.title.lower():
                        logger.info("[FocusGuard] Refocus SUCCESS")
                        return True

            except Exception as e:
                logger.warning(f"[FocusGuard] Refocus failed: {e}")

            time.sleep(0.2 * (attempt + 1))  # Backoff

        logger.error("[FocusGuard] All refocus attempts FAILED")
        return False

    def _get_active_title(self) -> Optional[str]:
        """Get current active window title."""
        active = self.computer.get_active_window()
        return active.title if active else None


class FocusLostError(Exception):
    """Raised when focus is lost and cannot be recovered."""

    pass
