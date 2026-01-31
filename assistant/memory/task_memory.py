"""
Task Memory - Persistent task context and learning.

Provides:
- Task history storage
- Context persistence across sessions
- Action pattern learning
"""

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TaskRecord:
    """Record of a completed task."""

    id: str
    task: str
    steps_completed: int
    steps_total: int
    success: bool
    duration_sec: float
    started_at: str
    completed_at: str
    error: str | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionPattern:
    """Learned action pattern."""

    trigger: str  # What triggers this pattern
    actions: list[dict[str, Any]]  # Sequence of actions
    success_rate: float
    use_count: int


class TaskMemory:
    """
    Persistent memory for task execution.

    Features:
    - Store task history
    - Learn from successful patterns
    - Provide context for future tasks
    """

    def __init__(self, storage_path: str | None = None):
        self._storage_path = Path(storage_path or self._default_path())
        self._storage_path.mkdir(parents=True, exist_ok=True)

        self._history_file = self._storage_path / "task_history.json"
        self._patterns_file = self._storage_path / "patterns.json"
        self._context_file = self._storage_path / "context.json"

        self._history: list[TaskRecord] = []
        self._patterns: dict[str, ActionPattern] = {}
        self._context: dict[str, Any] = {}

        self._load()

    def _default_path(self) -> str:
        return os.path.join(os.path.expanduser("~"), ".cowork", "memory")

    def _load(self):
        """Load from storage."""
        if self._history_file.exists():
            try:
                with open(self._history_file) as f:
                    data = json.load(f)
                self._history = [TaskRecord(**r) for r in data]
            except Exception:
                self._history = []

        if self._patterns_file.exists():
            try:
                with open(self._patterns_file) as f:
                    data = json.load(f)
                self._patterns = {k: ActionPattern(**v) for k, v in data.items()}
            except Exception:
                self._patterns = {}

        if self._context_file.exists():
            try:
                with open(self._context_file) as f:
                    self._context = json.load(f)
            except Exception:
                self._context = {}

    def _save(self):
        """Save to storage."""
        with open(self._history_file, "w") as f:
            json.dump([asdict(r) for r in self._history], f, indent=2)

        with open(self._patterns_file, "w") as f:
            json.dump({k: asdict(v) for k, v in self._patterns.items()}, f, indent=2)

        with open(self._context_file, "w") as f:
            json.dump(self._context, f, indent=2)

    def record_task(self, record: TaskRecord):
        """Record a completed task."""
        self._history.append(record)
        # Keep last 100 tasks
        self._history = self._history[-100:]
        self._save()

    def get_history(self, limit: int = 10) -> list[TaskRecord]:
        """Get recent task history."""
        return self._history[-limit:]

    def get_success_rate(self) -> float:
        """Get overall success rate."""
        if not self._history:
            return 0.0
        successful = sum(1 for t in self._history if t.success)
        return successful / len(self._history)

    def set_context(self, key: str, value: Any):
        """Set context value."""
        self._context[key] = value
        self._save()

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context value."""
        return self._context.get(key, default)

    def clear_context(self):
        """Clear all context."""
        self._context = {}
        self._save()

    def learn_pattern(self, trigger: str, actions: list[dict], success: bool):
        """Learn from action pattern."""
        if trigger in self._patterns:
            pattern = self._patterns[trigger]
            pattern.use_count += 1
            # Update success rate
            pattern.success_rate = (
                pattern.success_rate * (pattern.use_count - 1) + (1 if success else 0)
            ) / pattern.use_count
        else:
            self._patterns[trigger] = ActionPattern(
                trigger=trigger,
                actions=actions,
                success_rate=1.0 if success else 0.0,
                use_count=1,
            )
        self._save()

    def get_pattern(self, trigger: str) -> ActionPattern | None:
        """Get learned pattern for trigger."""
        return self._patterns.get(trigger)

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        return {
            "total_tasks": len(self._history),
            "success_rate": self.get_success_rate(),
            "patterns_learned": len(self._patterns),
            "context_keys": list(self._context.keys()),
        }
