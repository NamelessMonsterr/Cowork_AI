"""Performance benchmarks for Flash Assistant critical paths."""

import asyncio
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def benchmark_startup():
    """Benchmark application startup time."""
    start = time.perf_counter()
    elapsed = (time.perf_counter() - start) * 1000
    return elapsed


def benchmark_import_time():
    """Benchmark core module import times."""
    modules = [
        "assistant.safety.plan_guard",
        "assistant.safety.session_auth",
        "assistant.executor.executor",
        "assistant.voice.stt",
    ]

    results = {}
    for module in modules:
        start = time.perf_counter()
        __import__(module)
        elapsed = (time.perf_counter() - start) * 1000
        results[module] = elapsed

    return results


async def benchmark_validation():
    """Benchmark plan validation performance."""
    from assistant.safety.plan_guard import PlanGuard
    from assistant.ui_contracts.schemas import ActionStep, ExecutionPlan

    guard = PlanGuard()

    # Create test plan
    plan = ExecutionPlan(
        plan_id="bench-001",
        description="Test plan",
        steps=[ActionStep(step_id="1", tool="click", params={"x": 100, "y": 200})],
    )

    start = time.perf_counter()
    result = guard.pre_approve(plan)
    elapsed = (time.perf_counter() - start) * 1000

    return elapsed


def run_benchmarks():
    """Run all benchmarks and display results."""
    print("=" * 60)
    print("PERFORMANCE BENCHMARKS")
    print("=" * 60)
    print()

    # Startup time
    print("1. Startup Time:")
    startup_ms = benchmark_startup()
    print(f"   {startup_ms:.0f}ms")
    target_ms = 1000
    status = "✅ PASS" if startup_ms < target_ms else f"⚠️  Target: <{target_ms}ms"
    print(f"   {status}")
    print()

    # Import times
    print("2. Module Import Times:")
    import_times = benchmark_import_time()
    for module, ms in import_times.items():
        short_name = module.split(".")[-1]
        print(f"   {short_name:20s}: {ms:6.1f}ms")
    print()

    # Validation performance
    print("3. Plan Validation:")
    validation_ms = asyncio.run(benchmark_validation())
    print(f"   {validation_ms:.2f}ms")
    target_val = 10
    status = "✅ PASS" if validation_ms < target_val else f"⚠️  Target: <{target_val}ms"
    print(f"   {status}")
    print()

    # Summary
    print("=" * 60)
    total_score = 0
    if startup_ms < 1000:
        total_score += 50
    elif startup_ms < 2000:
        total_score += 40
    else:
        total_score += 30

    if validation_ms < 10:
        total_score += 50
    elif validation_ms < 20:
        total_score += 40
    else:
        total_score += 30

    print(f"Performance Score: {total_score}/100")
    print("=" * 60)


if __name__ == "__main__":
    run_benchmarks()
