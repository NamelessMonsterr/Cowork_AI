"""
Benchmark Runner - Orchestrates suite execution (W11.2).
"""

import asyncio
import glob
import logging
import os
from dataclasses import dataclass
from typing import Any

import yaml

from assistant.benchmark.harness import TaskHarness  # Pending W11.3
from assistant.benchmark.metrics import MetricsCollector
from assistant.benchmark.mode import benchmark_mode

logger = logging.getLogger("BenchmarkRunner")


@dataclass
class BenchmarkTask:
    id: str
    name: str
    category: str
    config: dict[str, Any]


class BenchmarkRunner:
    def __init__(self):
        self.tasks: list[BenchmarkTask] = []
        self.metrics = MetricsCollector()

    def load_suite(self, suite_path: str):
        """Load tasks from a directory or YAML file."""
        if os.path.isdir(suite_path):
            files = glob.glob(os.path.join(suite_path, "*.yaml"))
        else:
            files = [suite_path]

        count = 0
        for f in files:
            try:
                with open(f) as stream:
                    # YAML can have multiple docs separator ---
                    docs = yaml.safe_load_all(stream)
                    for doc in docs:
                        if not doc:
                            continue
                        task = BenchmarkTask(
                            id=doc.get("id", "unknown"),
                            name=doc.get("name", "Unknown Task"),
                            category=doc.get("category", "general"),
                            config=doc,
                        )
                        self.tasks.append(task)
                        count += 1
            except Exception as e:
                logger.error(f"Failed to load {f}: {e}")

        logger.info(f"Loaded {count} tasks from {suite_path}")

    async def run_suite(self, suite_path: str, repeat: int = 1):
        """Execute the loaded suite."""
        benchmark_mode.check()

        self.load_suite(suite_path)

        logger.info(f"🚀 Starting Benchmark Suite: {len(self.tasks)} Tasks x {repeat} Iterations")

        for i in range(repeat):
            logger.info(f"--- Iteration {i + 1}/{repeat} ---")
            for task in self.tasks:
                await self.run_task(task, iteration=i + 1)

        self.metrics.save_summary()
        logger.info("✅ Benchmark Suite Complete.")

    async def run_task(self, task: BenchmarkTask, iteration: int):
        logger.info(f"Running Task: {task.id} (Iter {iteration})")

        # 1. Reset Env (W11.4)
        # await reset_environment(task.config.get('reset'))

        # 2. Execute via Harness (W11.3)
        harness = TaskHarness()
        result = await harness.execute(task.config.get("plan", {}))

        status = "✅ PASS" if result["success"] else f"❌ FAIL ({result['error']})"
        logger.info(f"Task {task.id} Result: {status} (Dur: {result['duration']:.2f}s)")

        # 3. Log Result (W11.5)
        self.metrics.record(task.id, iteration, result)

        # Placeholder for now
        await asyncio.sleep(0.1)
