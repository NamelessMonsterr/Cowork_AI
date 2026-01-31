"""
Benchmark CLI - Entrypoint for running reliability suites (W11.2).

Usage:
    python -m assistant.benchmark.cli --suite suites/smoke.yaml --repeat 3
"""

import argparse
import asyncio
import logging
import os
import sys

# Setup Path
sys.path.append(os.getcwd())

from assistant.benchmark.mode import benchmark_mode
from assistant.benchmark.runner import BenchmarkRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BenchmarkCLI")


async def main():
    parser = argparse.ArgumentParser(description="CoworkAI Reliability Benchmark Runner")
    parser.add_argument("--suite", required=True, help="Path to suite YAML file")
    parser.add_argument("--repeat", type=int, default=1, help="Number of iterations per task")
    parser.add_argument("--dry-run", action="store_true", help="Validate setup without executing tasks")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed for failure injection")

    args = parser.parse_args()

    # 1. Enforce Safety Gate
    print("\n🔒 Reliability Benchmark Suite Starting...")
    if "COWORK_BENCHMARK_MODE" not in os.environ:
        print("❌ Error: COWORK_BENCHMARK_MODE=1 environment variable is missing.")
        sys.exit(1)

    try:
        benchmark_mode.enable(seed=args.seed)
    except PermissionError as e:
        print(f"❌ Safety Refusal: {e}")
        sys.exit(1)

    logger.info(f"Target Suite: {args.suite}")
    logger.info(f"Iterations: {args.repeat}")
    logger.info(f"Dry Run: {args.dry_run}")

    logger.info(f"Dry Run: {args.dry_run}")

    if args.dry_run:
        logger.info("✅ Dry Run Config Valid. Exiting.")
        return

    runner = BenchmarkRunner()
    await runner.run_suite(args.suite, args.repeat)


if __name__ == "__main__":
    asyncio.run(main())
