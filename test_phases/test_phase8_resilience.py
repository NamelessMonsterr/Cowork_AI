"""
Phase 8 Test: Error Handling & Resilience.

Tests:
1. Retry decorator
2. Circuit breaker
3. Error classification
4. Analytics
"""

import os
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from assistant.resilience import (
    Analytics,
    CircuitBreaker,
    CircuitState,
    ErrorClassifier,
    ErrorSeverity,
    RetryConfig,
    retry,
)


def test_retry_decorator():
    print("=== PHASE 8 TEST: RETRY DECORATOR ===\n")

    # Test 1: Successful retry
    print("1. Testing successful retry...")
    attempt_count = 0

    @retry(RetryConfig(max_retries=3, base_delay=0.1))
    def flaky_func():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ValueError("Temporary failure")
        return "success"

    result = flaky_func()
    assert result == "success"
    assert attempt_count == 3
    print(f"   ✅ Retry succeeded after {attempt_count} attempts")

    # Test 2: Config options
    print("2. Testing config options...")
    config = RetryConfig(max_retries=5, base_delay=0.5, exponential=True)
    assert config.max_retries == 5
    assert config.exponential == True
    print("   ✅ Config works")

    print("\n✅ Retry Decorator: PASSED")
    return True


def test_circuit_breaker():
    print("\n=== PHASE 8 TEST: CIRCUIT BREAKER ===\n")

    # Test 1: Initial state
    print("1. Testing initial state...")
    cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=1)
    assert cb.state == CircuitState.CLOSED
    print("   ✅ Initial state: CLOSED")

    # Test 2: Transition to OPEN
    print("2. Testing failure threshold...")
    for _ in range(3):
        cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert not cb.can_execute()
    print("   ✅ State after failures: OPEN")

    # Test 3: Recovery to HALF_OPEN
    print("3. Testing recovery...")
    time.sleep(1.1)  # Wait for recovery timeout
    assert cb.state == CircuitState.HALF_OPEN
    print("   ✅ State after timeout: HALF_OPEN")

    # Test 4: Reset
    print("4. Testing reset...")
    cb.reset()
    assert cb.state == CircuitState.CLOSED
    print("   ✅ Reset works")

    print("\n✅ Circuit Breaker: PASSED")
    return True


def test_error_classifier():
    print("\n=== PHASE 8 TEST: ERROR CLASSIFIER ===\n")

    # Test 1: Timeout error
    print("1. Testing timeout classification...")
    ctx = ErrorClassifier.classify(TimeoutError("Connection timeout"))
    assert ctx.severity == ErrorSeverity.MEDIUM
    assert ctx.recoverable == True
    print(f"   ✅ Timeout -> {ctx.severity.value}, recoverable={ctx.recoverable}")

    # Test 2: Permission error
    print("2. Testing permission classification...")
    ctx = ErrorClassifier.classify(PermissionError("Permission denied"))
    assert ctx.severity == ErrorSeverity.HIGH
    assert ctx.recoverable == False
    print(f"   ✅ Permission -> {ctx.severity.value}, recoverable={ctx.recoverable}")

    # Test 3: Suggestion
    print("3. Testing suggestions...")
    ctx = ErrorClassifier.classify(ConnectionError("Connection refused"))
    assert ctx.suggestion is not None
    print(f"   ✅ Suggestion: {ctx.suggestion}")

    print("\n✅ Error Classifier: PASSED")
    return True


def test_analytics():
    print("\n=== PHASE 8 TEST: ANALYTICS ===\n")

    # Test 1: Create analytics
    print("1. Testing analytics creation...")
    analytics = Analytics()
    print("   ✅ Analytics created")

    # Test 2: Track tasks
    print("2. Testing task tracking...")
    analytics.track_task("task-1", True, 5.0)
    analytics.track_task("task-2", False, 3.0)
    print("   ✅ Tasks tracked")

    # Test 3: Track actions
    print("3. Testing action tracking...")
    analytics.track_action("click")
    analytics.track_action("type")
    analytics.track_action("click")
    print("   ✅ Actions tracked")

    # Test 4: Generate report
    print("4. Testing report generation...")
    report = analytics.generate_report()
    assert report.total_tasks == 2
    assert report.successful_tasks == 1
    assert "click" in report.most_used_actions
    print(f"   ✅ Report: {report.total_tasks} tasks, {report.total_actions} actions")

    # Test 5: Metrics
    print("5. Testing metrics...")
    metrics = analytics.get_metrics()
    assert "counters" in metrics
    print("   ✅ Metrics collected")

    print("\n✅ Analytics: PASSED")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("       PHASE 8 ERROR HANDLING & RESILIENCE")
    print("=" * 50)

    results = []

    try:
        results.append(("Retry Decorator", test_retry_decorator()))
        results.append(("Circuit Breaker", test_circuit_breaker()))
        results.append(("Error Classifier", test_error_classifier()))
        results.append(("Analytics", test_analytics()))
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 50)
    print("       PHASE 8 RESULTS")
    print("=" * 50)

    all_pass = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_pass = False

    if all_pass:
        print("\n✨ PHASE 8 RESILIENCE: ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n❌ PHASE 8: SOME TESTS FAILED")
        sys.exit(1)
