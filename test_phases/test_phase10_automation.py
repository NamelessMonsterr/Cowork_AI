"""
Phase 10 Test: Scheduling & Automation.

Tests:
1. Scheduler
2. Delayed execution
3. Interval tasks
"""

import sys
import os
import time
import threading

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from assistant.automation import (
    Scheduler, ScheduleType, DelayedExecutor,
)


def test_scheduler():
    print("=== PHASE 10 TEST: SCHEDULER ===\n")
    
    # Test 1: Create scheduler
    print("1. Testing scheduler creation...")
    scheduler = Scheduler()
    scheduler.start()
    print("   ✅ Scheduler created and started")
    
    # Test 2: Schedule once
    print("2. Testing one-time scheduling...")
    executed = []
    task_id = scheduler.schedule_once(
        lambda: executed.append("once"),
        delay_sec=0.2,
        name="test_once"
    )
    assert task_id is not None
    print(f"   ✅ Task scheduled: {task_id}")
    
    # Test 3: Wait for execution
    print("3. Testing execution...")
    time.sleep(0.5)
    assert "once" in executed, f"Task should have executed, got: {executed}"
    print("   ✅ Task executed")
    
    # Test 4: Schedule interval
    print("4. Testing interval scheduling...")
    interval_count = []
    interval_id = scheduler.schedule_interval(
        lambda: interval_count.append(1),
        interval_sec=0.1,
        start_immediately=True
    )
    time.sleep(0.35)
    scheduler.cancel(interval_id)
    assert len(interval_count) >= 2, f"Should execute 2+ times, got: {len(interval_count)}"
    print(f"   ✅ Interval executed {len(interval_count)} times")
    
    # Test 5: Get tasks
    print("5. Testing get_tasks...")
    tasks = scheduler.get_tasks()
    print(f"   ✅ Got {len(tasks)} task(s)")
    
    scheduler.stop()
    
    print("\n✅ Scheduler: PASSED")
    return True


def test_delayed_executor():
    print("\n=== PHASE 10 TEST: DELAYED EXECUTOR ===\n")
    
    # Test 1: Create executor
    print("1. Testing executor creation...")
    executor = DelayedExecutor()
    print("   ✅ Executor created")
    
    # Test 2: Delay execution
    print("2. Testing delayed execution...")
    result = []
    executor.delay(lambda: result.append("delayed"), 0.2)
    assert len(result) == 0, "Should not execute yet"
    time.sleep(0.4)
    assert "delayed" in result, "Should have executed"
    print("   ✅ Delayed execution works")
    
    # Test 3: Cancel
    print("3. Testing cancel...")
    result2 = []
    task_id = executor.delay(lambda: result2.append("cancel"), 1.0)
    executor.cancel(task_id)
    time.sleep(0.2)
    assert len(result2) == 0, "Cancelled task should not execute"
    print("   ✅ Cancel works")
    
    executor.stop()
    
    print("\n✅ Delayed Executor: PASSED")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("       PHASE 10 SCHEDULING & AUTOMATION")
    print("=" * 50)
    
    results = []
    
    try:
        results.append(("Scheduler", test_scheduler()))
        results.append(("Delayed Executor", test_delayed_executor()))
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("       PHASE 10 RESULTS")
    print("=" * 50)
    
    all_pass = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_pass = False
    
    if all_pass:
        print("\n✨ PHASE 10: ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n❌ PHASE 10: SOME TESTS FAILED")
        sys.exit(1)
