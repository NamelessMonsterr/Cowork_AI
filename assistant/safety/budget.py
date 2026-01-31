"""
Action Budget - Global runaway protection.

Prevents the agent from running indefinitely by tracking:
- Total actions executed
- Total retries attempted
- Total runtime

If any budget is exceeded, forces pause + takeover.
"""

import time
import threading
from dataclasses import dataclass
from typing import Optional, Callable


class BudgetExceededError(Exception):
    """Raised when action budget is exceeded."""

    def __init__(self, message: str, budget_type: str, current: int, limit: int):
        super().__init__(message)
        self.budget_type = budget_type
        self.current = current
        self.limit = limit


@dataclass
class BudgetConfig:
    """Configuration for action budgets."""

    max_actions_per_task: int = 50  # Max actions in a single task
    max_retries_per_task: int = 20  # Max retries across all steps
    max_runtime_sec: int = 180  # 3 minutes max runtime per task
    max_consecutive_failures: int = 5  # Pause after N consecutive failures


@dataclass
class BudgetState:
    """Current budget state."""

    actions_executed: int = 0
    retries_attempted: int = 0
    consecutive_failures: int = 0
    task_start_time: float = 0
    last_action_time: float = 0
    is_paused: bool = False
    pause_reason: str = ""


class ActionBudget:
    """
    Tracks and enforces action budgets to prevent runaway execution.

    Usage:
        budget = ActionBudget(
            config=BudgetConfig(max_actions_per_task=50),
            on_budget_exceeded=lambda: executor.pause()
        )

        budget.start_task("download_file")

        # Before each action:
        budget.check_budget()  # Raises if exceeded

        # After each action:
        budget.record_action(success=True)

        budget.end_task()
    """

    def __init__(
        self,
        config: Optional[BudgetConfig] = None,
        on_budget_exceeded: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize ActionBudget.

        Args:
            config: Budget configuration
            on_budget_exceeded: Callback when any budget is exceeded
        """
        self._config = config or BudgetConfig()
        self._state = BudgetState()
        self._lock = threading.Lock()
        self._on_exceeded = on_budget_exceeded
        self._runtime_timer: Optional[threading.Timer] = None
        self._current_task: Optional[str] = None

    @property
    def state(self) -> BudgetState:
        """Get current state (read-only snapshot)."""
        with self._lock:
            return BudgetState(
                actions_executed=self._state.actions_executed,
                retries_attempted=self._state.retries_attempted,
                consecutive_failures=self._state.consecutive_failures,
                task_start_time=self._state.task_start_time,
                last_action_time=self._state.last_action_time,
                is_paused=self._state.is_paused,
                pause_reason=self._state.pause_reason,
            )

    @property
    def config(self) -> BudgetConfig:
        """Get current config."""
        return self._config

    def start_task(self, task_name: str) -> None:
        """
        Start tracking a new task.

        Args:
            task_name: Name of the task for logging
        """
        with self._lock:
            self._current_task = task_name
            self._state = BudgetState(
                task_start_time=time.time(),
                last_action_time=time.time(),
            )

            # Start runtime timer
            if self._runtime_timer:
                self._runtime_timer.cancel()

            self._runtime_timer = threading.Timer(
                self._config.max_runtime_sec, self._on_runtime_exceeded
            )
            self._runtime_timer.daemon = True
            self._runtime_timer.start()

    def end_task(self) -> dict:
        """
        End the current task and return summary.

        Returns:
            Summary of budget usage
        """
        with self._lock:
            if self._runtime_timer:
                self._runtime_timer.cancel()
                self._runtime_timer = None

            summary = {
                "task": self._current_task,
                "actions_executed": self._state.actions_executed,
                "retries_attempted": self._state.retries_attempted,
                "runtime_sec": time.time() - self._state.task_start_time
                if self._state.task_start_time
                else 0,
                "was_paused": self._state.is_paused,
                "pause_reason": self._state.pause_reason,
            }

            self._current_task = None
            return summary

    def check_budget(self) -> None:
        """
        Check if budget allows another action.

        Raises:
            BudgetExceededError: If any budget is exceeded
        """
        with self._lock:
            if self._state.is_paused:
                raise BudgetExceededError(
                    f"Execution paused: {self._state.pause_reason}", "paused", 0, 0
                )

            # Check actions
            if self._state.actions_executed >= self._config.max_actions_per_task:
                self._trigger_exceeded(
                    "actions",
                    self._state.actions_executed,
                    self._config.max_actions_per_task,
                )

            # Check retries
            if self._state.retries_attempted >= self._config.max_retries_per_task:
                self._trigger_exceeded(
                    "retries",
                    self._state.retries_attempted,
                    self._config.max_retries_per_task,
                )

            # Check consecutive failures
            if (
                self._state.consecutive_failures
                >= self._config.max_consecutive_failures
            ):
                self._trigger_exceeded(
                    "consecutive_failures",
                    self._state.consecutive_failures,
                    self._config.max_consecutive_failures,
                )

            # Check runtime
            if self._state.task_start_time > 0:
                runtime = time.time() - self._state.task_start_time
                if runtime >= self._config.max_runtime_sec:
                    self._trigger_exceeded(
                        "runtime", int(runtime), self._config.max_runtime_sec
                    )

    def record_action(self, success: bool, was_retry: bool = False) -> None:
        """
        Record an action execution.

        Args:
            success: Whether the action succeeded
            was_retry: Whether this was a retry attempt
        """
        with self._lock:
            self._state.actions_executed += 1
            self._state.last_action_time = time.time()

            if was_retry:
                self._state.retries_attempted += 1

            if success:
                self._state.consecutive_failures = 0
            else:
                self._state.consecutive_failures += 1

    def pause(self, reason: str) -> None:
        """
        Manually pause execution.

        Args:
            reason: Why execution is paused
        """
        with self._lock:
            self._state.is_paused = True
            self._state.pause_reason = reason

    def resume(self) -> None:
        """Resume execution after pause."""
        with self._lock:
            self._state.is_paused = False
            self._state.pause_reason = ""
            self._state.consecutive_failures = 0

    def get_remaining(self) -> dict:
        """
        Get remaining budget.

        Returns:
            Dictionary with remaining budget for each limit
        """
        with self._lock:
            runtime = (
                time.time() - self._state.task_start_time
                if self._state.task_start_time
                else 0
            )

            return {
                "actions_remaining": max(
                    0, self._config.max_actions_per_task - self._state.actions_executed
                ),
                "retries_remaining": max(
                    0, self._config.max_retries_per_task - self._state.retries_attempted
                ),
                "runtime_remaining_sec": max(
                    0, self._config.max_runtime_sec - int(runtime)
                ),
                "failures_until_pause": max(
                    0,
                    self._config.max_consecutive_failures
                    - self._state.consecutive_failures,
                ),
            }

    def _trigger_exceeded(self, budget_type: str, current: int, limit: int) -> None:
        """Internal: trigger budget exceeded."""
        self._state.is_paused = True
        self._state.pause_reason = f"{budget_type} budget exceeded ({current}/{limit})"

        if self._on_exceeded:
            # Call outside lock to prevent deadlock
            threading.Thread(
                target=self._on_exceeded, args=(self._state.pause_reason,), daemon=True
            ).start()

        raise BudgetExceededError(
            f"Budget exceeded: {budget_type}", budget_type, current, limit
        )

    def _on_runtime_exceeded(self) -> None:
        """Called when runtime timer expires."""
        with self._lock:
            if not self._state.is_paused:
                self._state.is_paused = True
                self._state.pause_reason = (
                    f"Runtime exceeded ({self._config.max_runtime_sec}s)"
                )

        if self._on_exceeded:
            self._on_exceeded(self._state.pause_reason)
