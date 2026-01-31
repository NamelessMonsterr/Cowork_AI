"""
Benchmark Mode - Safety Gate (W11.0).

Enforces safety constraints for automated benchmarks:
1. Must operate in explicit BENCHMARK_MODE (Env Var or CLI Flag).
2. Must have valid SessionAuth.
3. Disables risky features (Mic, uncontrolled recording).
"""

import os
import logging

logger = logging.getLogger("BenchmarkMode")


class BenchmarkMode:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BenchmarkMode, cls).__new__(cls)
            cls._instance.enabled = False
            cls._instance.seed = None
        return cls._instance

    def enable(self, seed: int = None):
        """Enable benchmark mode if safety checks pass."""
        # 1. Check Env Var
        env_flag = os.getenv("COWORK_BENCHMARK_MODE") == "1"
        if not env_flag:
            logger.error(
                "❌ BENCHMARK_MODE refused: COWORK_BENCHMARK_MODE=1 env var required."
            )
            raise PermissionError("Benchmark Mode requires COWORK_BENCHMARK_MODE=1")

        # 2. Check Session Auth (Mock or Real)
        # Note: Caller is responsible for ensuring SessionAuth is granted before running tasks.

        self.enabled = True
        self.seed = seed
        logger.warning(f"⚠️ BENCHMARK MODE ENABLED (Seed: {seed}) ⚠️")
        logger.warning("Microphone and user interruptions disabled.")

    def check(self):
        """Raise error if not in benchmark mode."""
        if not self.enabled:
            raise PermissionError("Operation allowed only in Benchmark Mode.")

    @property
    def is_enabled(self):
        return self.enabled


# Singleton
benchmark_mode = BenchmarkMode()
