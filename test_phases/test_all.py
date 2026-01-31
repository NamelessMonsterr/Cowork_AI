"""
Complete Test Suite - Phases 1, 2 & 3.

Runs all test scripts in sequence and reports combined results.

Usage:
    python test_all.py

Exit Codes:
    0 - All tests passed
    1 - Some tests failed
"""

import os
import subprocess
import sys
import time

# Test scripts in execution order
TEST_SCRIPTS = [
    # Phase 1: Foundation
    ("Phase 1: Core & Safety", "test_step1.py"),
    ("Phase 1: Verification", "test_step2.py"),
    ("Phase 1: Build", "test_build.py"),
    # Phase 2: Power
    ("Phase 2: Strategy Fallback", "test_phase2_fallback.py"),
    ("Phase 2: UIA (Notepad)", "test_phase2_uia.py"),
    # Phase 3: Trust
    ("Phase 3: Trust & Safety", "test_phase3_safety.py"),
    # Phase 4: Voice
    ("Phase 4: Voice Mode", "test_phase4_voice.py"),
    # Phase 5: Performance
    ("Phase 5: Performance", "test_phase5_performance.py"),
    # Phase 6: Packaging
    ("Phase 6: Packaging", "test_phase6_packaging.py"),
    # Phase 7: Advanced
    ("Phase 7: Advanced", "test_phase7_advanced.py"),
    # Phase 8: Resilience
    ("Phase 8: Resilience", "test_phase8_resilience.py"),
    # Phase 9: Config
    ("Phase 9: Config", "test_phase9_config.py"),
    # Phase 10: Automation
    ("Phase 10: Automation", "test_phase10_automation.py"),
]


def run_test(name: str, script: str) -> tuple[bool, float]:
    """
    Run a test script and return (success, duration).
    """
    start = time.time()

    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script)

    if not os.path.exists(script_path):
        print(f"  ⚠️ Script not found: {script}")
        return False, 0

    try:
        # Set UTF-8 encoding to handle emoji characters
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        result = subprocess.run(
            [sys.executable, script_path],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout per test
            env=env,
            encoding="utf-8",
            errors="replace",
        )

        duration = time.time() - start
        success = result.returncode == 0

        if not success:
            # Show error output
            print("\n  --- Error Output ---")
            if result.stderr:
                print(result.stderr[-500:])  # Last 500 chars
            if result.stdout:
                print(result.stdout[-500:])
            print("  --- End Error ---\n")

        return success, duration

    except subprocess.TimeoutExpired:
        print("  ⚠️ Test timed out after 60s")
        return False, 60
    except Exception as e:
        print(f"  ⚠️ Error running test: {e}")
        return False, time.time() - start


def main():
    print("=" * 60)
    print("     COWORK AI ASSISTANT - COMPLETE TEST SUITE")
    print("     Phases 1, 2 & 3")
    print("=" * 60)
    print()

    results = []
    total_start = time.time()

    for name, script in TEST_SCRIPTS:
        print(f"Running: {name}...")
        success, duration = run_test(name, script)
        results.append((name, script, success, duration))

        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} ({duration:.1f}s)")
        print()

    total_duration = time.time() - total_start

    # Summary
    print("=" * 60)
    print("     TEST RESULTS SUMMARY")
    print("=" * 60)
    print()

    passed = 0
    failed = 0

    for name, script, success, duration in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
        if success:
            passed += 1
        else:
            failed += 1

    print()
    print(f"  Total: {passed + failed} tests")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Duration: {total_duration:.1f}s")
    print()

    if failed == 0:
        print("=" * 60)
        print("  ✨ ALL TESTS PASSED - SYSTEM VERIFIED")
        print("=" * 60)
        return 0
    else:
        print("=" * 60)
        print("  ❌ SOME TESTS FAILED - CHECK OUTPUT ABOVE")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
