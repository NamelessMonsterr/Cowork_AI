"""
Human Takeover Manager.

Handles scenarios where the agent needs human intervention:
- Pause automation and notify user
- Record user actions for learning
- Resume automation after human completes task
- Timeout handling

This is the "supervised mode" controller.
"""

import time
import threading
from typing import Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum


class TakeoverReason(str, Enum):
    """Reasons for requesting human takeover."""

    SENSITIVE_SCREEN = "sensitive_screen"
    VERIFICATION_FAILED = "verification_failed"
    BUDGET_EXCEEDED = "budget_exceeded"
    USER_REQUESTED = "user_requested"
    UNSAFE_ENVIRONMENT = "unsafe_environment"
    UNKNOWN_UI = "unknown_ui"
    ERROR = "error"


class TakeoverState(str, Enum):
    """Current state of takeover mode."""

    INACTIVE = "inactive"
    REQUESTED = "requested"
    ACTIVE = "active"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"


@dataclass
class TakeoverRequest:
    """A request for human takeover."""

    id: str
    reason: TakeoverReason
    message: str
    context: dict
    requested_at: float
    timeout_sec: float = 300.0  # 5 minute default timeout

    @property
    def is_expired(self) -> bool:
        return time.time() > (self.requested_at + self.timeout_sec)


@dataclass
class TakeoverSession:
    """An active takeover session."""

    request: TakeoverRequest
    started_at: float
    ended_at: Optional[float] = None
    user_actions: List[dict] = field(default_factory=list)
    outcome: str = ""

    @property
    def duration_sec(self) -> float:
        end = self.ended_at or time.time()
        return end - self.started_at


class TakeoverManager:
    """
    Manages human takeover mode.

    Usage:
        manager = TakeoverManager(
            on_takeover_requested=lambda req: notify_user(req),
            on_takeover_completed=lambda session: resume_automation(),
        )

        # Request takeover
        manager.request_takeover(
            reason=TakeoverReason.SENSITIVE_SCREEN,
            message="Please enter your password",
            context={"window": "Login Page"}
        )

        # User starts takeover
        manager.start_takeover()

        # User completes
        manager.complete_takeover(outcome="Password entered")
    """

    def __init__(
        self,
        on_takeover_requested: Optional[Callable[[TakeoverRequest], None]] = None,
        on_takeover_completed: Optional[Callable[[TakeoverSession], None]] = None,
        on_timeout: Optional[Callable[[TakeoverRequest], None]] = None,
        default_timeout_sec: float = 300.0,
    ):
        """
        Initialize TakeoverManager.

        Args:
            on_takeover_requested: Callback when takeover is requested
            on_takeover_completed: Callback when takeover completes
            on_timeout: Callback when takeover times out
            default_timeout_sec: Default timeout for requests
        """
        self._on_requested = on_takeover_requested
        self._on_completed = on_takeover_completed
        self._on_timeout = on_timeout
        self._default_timeout = default_timeout_sec

        self._state = TakeoverState.INACTIVE
        self._current_request: Optional[TakeoverRequest] = None
        self._current_session: Optional[TakeoverSession] = None
        self._request_counter = 0

        self._lock = threading.Lock()
        self._timeout_timer: Optional[threading.Timer] = None

        # History for learning
        self._history: List[TakeoverSession] = []

    @property
    def state(self) -> TakeoverState:
        return self._state

    @property
    def is_active(self) -> bool:
        return self._state in (TakeoverState.REQUESTED, TakeoverState.ACTIVE)

    @property
    def current_request(self) -> Optional[TakeoverRequest]:
        return self._current_request

    def request_takeover(
        self,
        reason: TakeoverReason,
        message: str,
        context: dict = None,
        timeout_sec: float = None,
    ) -> TakeoverRequest:
        """
        Request human takeover.

        Args:
            reason: Why takeover is needed
            message: Message to show user
            context: Additional context dict
            timeout_sec: Override default timeout

        Returns:
            TakeoverRequest object
        """
        with self._lock:
            self._request_counter += 1

            request = TakeoverRequest(
                id=f"takeover_{self._request_counter}",
                reason=reason,
                message=message,
                context=context or {},
                requested_at=time.time(),
                timeout_sec=timeout_sec or self._default_timeout,
            )

            self._current_request = request
            self._state = TakeoverState.REQUESTED

            # Start timeout timer
            self._start_timeout_timer(request)

            # Notify
            if self._on_requested:
                self._on_requested(request)

            return request

    def start_takeover(self) -> Optional[TakeoverSession]:
        """
        User acknowledges and starts takeover.

        Returns:
            TakeoverSession if started, None if no pending request
        """
        with self._lock:
            if self._state != TakeoverState.REQUESTED:
                return None

            if not self._current_request:
                return None

            # Cancel timeout
            self._cancel_timeout_timer()

            session = TakeoverSession(
                request=self._current_request,
                started_at=time.time(),
            )

            self._current_session = session
            self._state = TakeoverState.ACTIVE

            return session

    def record_action(self, action: dict) -> None:
        """
        Record a user action during takeover.

        Args:
            action: Action dict (e.g., {"type": "click", "x": 100, "y": 200})
        """
        with self._lock:
            if self._current_session:
                action["timestamp"] = time.time()
                self._current_session.user_actions.append(action)

    def complete_takeover(
        self, outcome: str = "completed"
    ) -> Optional[TakeoverSession]:
        """
        Complete the current takeover session.

        Args:
            outcome: Description of outcome

        Returns:
            Completed TakeoverSession
        """
        with self._lock:
            if self._state != TakeoverState.ACTIVE:
                return None

            if not self._current_session:
                return None

            self._current_session.ended_at = time.time()
            self._current_session.outcome = outcome

            session = self._current_session
            self._history.append(session)

            self._state = TakeoverState.COMPLETED
            self._current_request = None
            self._current_session = None

            # Notify
            if self._on_completed:
                self._on_completed(session)

            # Reset state for next automation
            self._state = TakeoverState.INACTIVE

            return session

    def cancel_takeover(self, reason: str = "cancelled") -> None:
        """Cancel a pending or active takeover."""
        with self._lock:
            self._cancel_timeout_timer()

            if self._current_session:
                self._current_session.ended_at = time.time()
                self._current_session.outcome = f"Cancelled: {reason}"
                self._history.append(self._current_session)

            self._state = TakeoverState.INACTIVE
            self._current_request = None
            self._current_session = None

    def get_history(self, limit: int = 10) -> List[TakeoverSession]:
        """Get recent takeover history."""
        return self._history[-limit:]

    def get_status(self) -> dict:
        """Get current takeover status."""
        return {
            "state": self._state.value,
            "is_active": self.is_active,
            "current_request": {
                "id": self._current_request.id,
                "reason": self._current_request.reason.value,
                "message": self._current_request.message,
                "is_expired": self._current_request.is_expired,
            }
            if self._current_request
            else None,
            "session_duration": self._current_session.duration_sec
            if self._current_session
            else 0,
            "history_count": len(self._history),
        }

    def _start_timeout_timer(self, request: TakeoverRequest) -> None:
        """Start timeout timer for request."""
        self._cancel_timeout_timer()

        def on_timeout():
            with self._lock:
                if (
                    self._state == TakeoverState.REQUESTED
                    and self._current_request == request
                ):
                    self._state = TakeoverState.TIMED_OUT
                    self._current_request = None

                    if self._on_timeout:
                        self._on_timeout(request)

        self._timeout_timer = threading.Timer(request.timeout_sec, on_timeout)
        self._timeout_timer.daemon = True
        self._timeout_timer.start()

    def _cancel_timeout_timer(self) -> None:
        """Cancel any active timeout timer."""
        if self._timeout_timer:
            self._timeout_timer.cancel()
            self._timeout_timer = None
