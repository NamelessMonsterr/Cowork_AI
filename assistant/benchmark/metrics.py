"""
Metrics Collector - Structured logging for Benchmark Suite (W11.5).
"""

import time
import json
import os
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from assistant.benchmark.failure_taxonomy import classify_error

logger = logging.getLogger("MetricsCollector")


@dataclass
class TaskResult:
    task_id: str
    iteration: int
    success: bool
    duration: float
    steps_total: int
    steps_completed: int
    error: Optional[str] = None
    failure_category: Optional[str] = None
    recovery_attempts: int = 0
    timestamp: float = 0.0


class MetricsCollector:
    def __init__(self, output_dir: str = ".conversations/benchmarks"):
        self.output_dir = os.path.join(output_dir, f"run_{int(time.time())}")
        os.makedirs(self.output_dir, exist_ok=True)
        self.results: List[TaskResult] = []

        # Open log streams
        self.metrics_file = open(
            os.path.join(self.output_dir, "metrics.jsonl"), "a", encoding="utf-8"
        )

    def record(self, task_id: str, iteration: int, result_data: Dict[str, Any]):
        """Record a task execution result."""
        error_msg = result_data.get("error")
        category = classify_error(error_msg).value if error_msg else None

        record = TaskResult(
            task_id=task_id,
            iteration=iteration,
            success=result_data["success"],
            duration=result_data["duration"],
            steps_total=result_data["steps_total"],
            steps_completed=result_data["steps_completed"],
            error=error_msg,
            failure_category=category,
            timestamp=time.time(),
        )

        self.results.append(record)

        # Write to JSONL line-by-line
        try:
            line = json.dumps(asdict(record))
            self.metrics_file.write(line + "\n")
            self.metrics_file.flush()
        except Exception as e:
            logger.error(f"Failed to log metric: {e}")

    def save_summary(self):
        """Generate summary report (W11.7 placeholder)."""
        logger.info(f"Saving summary to {self.output_dir}")
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        rate = (passed / total * 100) if total > 0 else 0

        summary = {
            "total_tasks": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": f"{rate:.1f}%",
            "duration": sum(r.duration for r in self.results),
        }

        with open(os.path.join(self.output_dir, "summary.json"), "w") as f:
            json.dump(summary, f, indent=2)

        return summary
