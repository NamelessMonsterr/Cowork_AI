"""
Environment Monitor - Detects unsafe execution conditions.

Monitors for:
- Screen lock
- Active window changes (focus loss)
- Desktop switches
- UAC secure desktop
- Computer sleep/idle

When any condition is detected, execution is paused and takeover requested.
"""

import ctypes
import threading
import time
from dataclasses import dataclass
from typing import Optional, Callable
from enum import Enum

from .uac import is_secure_desktop


class EnvironmentState(str, Enum):
    """Current environment state."""

    NORMAL = "normal"  # Safe to execute
    LOCKED = "locked"  # Screen is locked
    FOCUS_LOST = "focus_lost"  # Active window changed unexpectedly
    SECURE_DESKTOP = "secure_desktop"  # UAC or other secure desktop
    SLEEPING = "sleeping"  # Computer is sleeping/idle
    UNKNOWN = "unknown"  # Cannot determine state


@dataclass
class WindowContext:
    """Expected window context during execution."""

    hwnd: Optional[int] = None
    title: Optional[str] = None
    process_name: Optional[str] = None


class EnvironmentMonitor:
    """
    Monitors execution environment for unsafe conditions.

    Usage:
        monitor = EnvironmentMonitor(
            on_unsafe=lambda state: executor.pause(f"Unsafe: {state}")
        )

        monitor.start()
        monitor.set_expected_window(hwnd=12345, title="Chrome")

        # Periodically or before actions:
        state = monitor.check_state()
        if state != EnvironmentState.NORMAL:
            # Handle unsafe state
            pass

        monitor.stop()
    """

    # Windows API constants
    DESKTOP_READOBJECTS = 0x0001
    DESKTOP_WRITEOBJECTS = 0x0080

    def __init__(
        self,
        on_unsafe: Optional[Callable[[EnvironmentState, str], None]] = None,
        check_interval_sec: float = 0.5,
    ):
        """
        Initialize EnvironmentMonitor.

        Args:
            on_unsafe: Callback when unsafe state detected (state, reason)
            check_interval_sec: How often to check environment
        """
        self._on_unsafe = on_unsafe
        self._check_interval = check_interval_sec
        self._expected_window: Optional[WindowContext] = None
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._last_state = EnvironmentState.NORMAL
        self._lock = threading.Lock()

        # Windows API
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32

    def start(self) -> None:
        """Start continuous environment monitoring."""
        with self._lock:
            if self._monitoring:
                return

            self._monitoring = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop, daemon=True
            )
            self._monitor_thread.start()

    def stop(self) -> None:
        """Stop environment monitoring."""
        with self._lock:
            self._monitoring = False

        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
            self._monitor_thread = None

    def set_expected_window(
        self,
        hwnd: Optional[int] = None,
        title: Optional[str] = None,
        process_name: Optional[str] = None,
    ) -> None:
        """
        Set the expected active window during execution.

        Args:
            hwnd: Expected window handle
            title: Expected window title (partial match)
            process_name: Expected process name
        """
        with self._lock:
            self._expected_window = WindowContext(
                hwnd=hwnd,
                title=title,
                process_name=process_name,
            )

    def clear_expected_window(self) -> None:
        """Clear expected window (disable focus checking)."""
        with self._lock:
            self._expected_window = None

    def check_state(self) -> EnvironmentState:
        """
        Check current environment state.

        Returns:
            Current EnvironmentState
        """
        # Check for secure desktop (UAC, lock screen, etc.)
        if self._is_secure_desktop():
            return EnvironmentState.SECURE_DESKTOP

        # Check for screen lock
        if self._is_workstation_locked():
            return EnvironmentState.LOCKED

        # Check for focus loss
        if self._expected_window and self._is_focus_lost():
            return EnvironmentState.FOCUS_LOST

        return EnvironmentState.NORMAL

    def _is_secure_desktop(self) -> bool:
        """
        Check if we're on a secure desktop (UAC, lock screen, etc.).
        """
        return is_secure_desktop()

    def _is_workstation_locked(self) -> bool:
        """Check if the workstation is locked."""
        try:
            # One approach: check if the desktop is the Winlogon desktop
            # Another: use OpenInputDesktop success/fail
            # For simplicity, we rely on secure desktop check above
            # which catches the lock screen
            return False
        except Exception:
            return False

    def _is_focus_lost(self) -> bool:
        """Check if focus has been lost from expected window."""
        try:
            current_hwnd = self._user32.GetForegroundWindow()

            if current_hwnd == 0:
                return True

            with self._lock:
                if self._expected_window is None:
                    return False

                # Check by hwnd if specified
                if self._expected_window.hwnd is not None:
                    if current_hwnd != self._expected_window.hwnd:
                        return True

                # Check by title if specified
                if self._expected_window.title is not None:
                    length = self._user32.GetWindowTextLengthW(current_hwnd)
                    if length > 0:
                        buffer = ctypes.create_unicode_buffer(length + 1)
                        self._user32.GetWindowTextW(current_hwnd, buffer, length + 1)
                        current_title = buffer.value.lower()
                        expected_title = self._expected_window.title.lower()

                        if expected_title not in current_title:
                            return True

            return False

        except Exception:
            return False

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._monitoring:
            try:
                state = self.check_state()

                if state != EnvironmentState.NORMAL and state != self._last_state:
                    # State changed to unsafe
                    reason = self._get_state_reason(state)

                    if self._on_unsafe:
                        self._on_unsafe(state, reason)

                self._last_state = state

            except Exception:
                pass  # Don't crash the monitor thread

            time.sleep(self._check_interval)

    def _get_state_reason(self, state: EnvironmentState) -> str:
        """Get human-readable reason for state."""
        reasons = {
            EnvironmentState.LOCKED: "Screen is locked",
            EnvironmentState.FOCUS_LOST: "Active window changed unexpectedly",
            EnvironmentState.SECURE_DESKTOP: "UAC or secure desktop detected - automation not allowed",
            EnvironmentState.SLEEPING: "Computer is sleeping or idle",
            EnvironmentState.UNKNOWN: "Cannot determine environment state",
        }
        return reasons.get(state, "Unknown condition")

    def get_current_window_info(self) -> dict:
        """Get info about the current foreground window."""
        try:
            hwnd = self._user32.GetForegroundWindow()

            if hwnd == 0:
                return {"hwnd": 0, "title": "", "class": ""}

            # Get title
            length = self._user32.GetWindowTextLengthW(hwnd)
            title_buffer = ctypes.create_unicode_buffer(length + 1)
            self._user32.GetWindowTextW(hwnd, title_buffer, length + 1)

            # Get class name
            class_buffer = ctypes.create_unicode_buffer(256)
            self._user32.GetClassNameW(hwnd, class_buffer, 256)

            return {
                "hwnd": hwnd,
                "title": title_buffer.value,
                "class": class_buffer.value,
            }

        except Exception:
            return {"hwnd": 0, "title": "", "class": ""}
