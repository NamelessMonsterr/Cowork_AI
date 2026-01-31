"""
Scheduling & Automation Module.

Provides:
- Task scheduling
- Cron-like expressions
- Delayed execution
"""

import heapq
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class ScheduleType(str, Enum):
    """Schedule types."""

    ONCE = "once"
    INTERVAL = "interval"
    DAILY = "daily"
    CRON = "cron"


@dataclass
class ScheduledTask:
    """A scheduled task."""

    id: str
    name: str
    callback: Callable
    schedule_type: ScheduleType
    next_run: float
    interval_sec: float = 0
    enabled: bool = True
    run_count: int = 0
    last_run: float | None = None

    def __lt__(self, other):
        return self.next_run < other.next_run


class Scheduler:
    """
    Task scheduler with interval and one-time execution.

    Features:
    - Schedule callbacks
    - Interval execution
    - Priority queue
    """

    def __init__(self):
        self._tasks: dict[str, ScheduledTask] = {}
        self._queue: list[ScheduledTask] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._task_counter = 0

    def _generate_id(self) -> str:
        self._task_counter += 1
        return f"task_{self._task_counter}"

    def schedule_once(self, callback: Callable, delay_sec: float, name: str = "") -> str:
        """Schedule a one-time task."""
        task_id = self._generate_id()
        task = ScheduledTask(
            id=task_id,
            name=name or task_id,
            callback=callback,
            schedule_type=ScheduleType.ONCE,
            next_run=time.time() + delay_sec,
        )

        with self._lock:
            self._tasks[task_id] = task
            heapq.heappush(self._queue, task)

        return task_id

    def schedule_interval(
        self,
        callback: Callable,
        interval_sec: float,
        name: str = "",
        start_immediately: bool = False,
    ) -> str:
        """Schedule a recurring task."""
        task_id = self._generate_id()
        next_run = time.time() if start_immediately else time.time() + interval_sec

        task = ScheduledTask(
            id=task_id,
            name=name or task_id,
            callback=callback,
            schedule_type=ScheduleType.INTERVAL,
            next_run=next_run,
            interval_sec=interval_sec,
        )

        with self._lock:
            self._tasks[task_id] = task
            heapq.heappush(self._queue, task)

        return task_id

    def cancel(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].enabled = False
                del self._tasks[task_id]
                return True
        return False

    def start(self):
        """Start the scheduler."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _run_loop(self):
        """Main scheduler loop."""
        while self._running:
            now = time.time()

            with self._lock:
                while self._queue and self._queue[0].next_run <= now:
                    task = heapq.heappop(self._queue)

                    if not task.enabled or task.id not in self._tasks:
                        continue

                    # Execute task
                    try:
                        task.callback()
                    except Exception as e:
                        print(f"Scheduler: Task {task.name} failed: {e}")

                    task.run_count += 1
                    task.last_run = now

                    # Reschedule if interval
                    if task.schedule_type == ScheduleType.INTERVAL:
                        task.next_run = now + task.interval_sec
                        heapq.heappush(self._queue, task)

            time.sleep(0.1)

    def get_tasks(self) -> list[dict[str, Any]]:
        """Get list of scheduled tasks."""
        with self._lock:
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "type": t.schedule_type.value,
                    "next_run": datetime.fromtimestamp(t.next_run).isoformat(),
                    "run_count": t.run_count,
                    "enabled": t.enabled,
                }
                for t in self._tasks.values()
            ]


class DelayedExecutor:
    """Execute actions with delays."""

    def __init__(self):
        self._scheduler = Scheduler()
        self._scheduler.start()

    def delay(self, callback: Callable, seconds: float) -> str:
        """Execute callback after delay."""
        return self._scheduler.schedule_once(callback, seconds)

    def repeat(self, callback: Callable, interval: float) -> str:
        """Execute callback repeatedly."""
        return self._scheduler.schedule_interval(callback, interval)

    def cancel(self, task_id: str):
        """Cancel a delayed task."""
        self._scheduler.cancel(task_id)

    def stop(self):
        """Stop the executor."""
        self._scheduler.stop()


# Global scheduler
_scheduler: Scheduler | None = None


def get_scheduler() -> Scheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
        _scheduler.start()
    return _scheduler
