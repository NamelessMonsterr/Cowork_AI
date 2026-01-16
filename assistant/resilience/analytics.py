"""
Analytics & Reporting Module.

Provides:
- Usage analytics
- Performance metrics
- Report generation
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


@dataclass
class Metric:
    """Single metric data point."""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """
    Collects and aggregates metrics.
    """
    
    def __init__(self, max_points: int = 1000):
        self._metrics: Dict[str, List[Metric]] = defaultdict(list)
        self._counters: Dict[str, int] = defaultdict(int)
        self._max_points = max_points
    
    def record(self, name: str, value: float, **tags):
        """Record a metric value."""
        metric = Metric(
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags,
        )
        self._metrics[name].append(metric)
        
        # Trim old points
        if len(self._metrics[name]) > self._max_points:
            self._metrics[name] = self._metrics[name][-self._max_points:]
    
    def increment(self, name: str, amount: int = 1):
        """Increment a counter."""
        self._counters[name] += amount
    
    def get_counter(self, name: str) -> int:
        return self._counters.get(name, 0)
    
    def get_average(self, name: str) -> float:
        """Get average value for metric."""
        values = self._metrics.get(name, [])
        if not values:
            return 0.0
        return sum(m.value for m in values) / len(values)
    
    def get_max(self, name: str) -> float:
        values = self._metrics.get(name, [])
        if not values:
            return 0.0
        return max(m.value for m in values)
    
    def get_min(self, name: str) -> float:
        values = self._metrics.get(name, [])
        if not values:
            return 0.0
        return min(m.value for m in values)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        return {
            "counters": dict(self._counters),
            "metrics": {
                name: {
                    "count": len(values),
                    "avg": self.get_average(name),
                    "max": self.get_max(name),
                    "min": self.get_min(name),
                }
                for name, values in self._metrics.items()
            }
        }


@dataclass
class UsageReport:
    """Usage report data."""
    period_start: str
    period_end: str
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    total_actions: int
    avg_task_duration_sec: float
    most_used_actions: List[str]
    error_summary: Dict[str, int]


class Analytics:
    """
    Tracks usage and generates reports.
    """
    
    def __init__(self):
        self._metrics = MetricsCollector()
        self._session_start = time.time()
        self._tasks: List[Dict] = []
        self._actions: List[str] = []
        self._errors: List[str] = []
    
    def track_task(self, task_id: str, success: bool, duration: float):
        """Track task completion."""
        self._tasks.append({
            "id": task_id,
            "success": success,
            "duration": duration,
            "timestamp": time.time(),
        })
        self._metrics.record("task_duration", duration)
        self._metrics.increment("tasks_total")
        if success:
            self._metrics.increment("tasks_success")
        else:
            self._metrics.increment("tasks_failed")
    
    def track_action(self, action_type: str):
        """Track action execution."""
        self._actions.append(action_type)
        self._metrics.increment(f"action_{action_type}")
        self._metrics.increment("actions_total")
    
    def track_error(self, error_type: str):
        """Track error occurrence."""
        self._errors.append(error_type)
        self._metrics.increment(f"error_{error_type}")
        self._metrics.increment("errors_total")
    
    def generate_report(self) -> UsageReport:
        """Generate usage report."""
        now = time.time()
        
        total = len(self._tasks)
        successful = sum(1 for t in self._tasks if t["success"])
        failed = total - successful
        
        durations = [t["duration"] for t in self._tasks]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Most used actions
        action_counts = defaultdict(int)
        for action in self._actions:
            action_counts[action] += 1
        most_used = sorted(action_counts.keys(), key=lambda x: action_counts[x], reverse=True)[:5]
        
        # Error summary
        error_counts = defaultdict(int)
        for error in self._errors:
            error_counts[error] += 1
        
        return UsageReport(
            period_start=datetime.fromtimestamp(self._session_start).isoformat(),
            period_end=datetime.fromtimestamp(now).isoformat(),
            total_tasks=total,
            successful_tasks=successful,
            failed_tasks=failed,
            total_actions=len(self._actions),
            avg_task_duration_sec=avg_duration,
            most_used_actions=most_used,
            error_summary=dict(error_counts),
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get raw metrics."""
        return self._metrics.get_summary()


# Global analytics instance
_analytics: Optional[Analytics] = None


def get_analytics() -> Analytics:
    global _analytics
    if _analytics is None:
        _analytics = Analytics()
    return _analytics
