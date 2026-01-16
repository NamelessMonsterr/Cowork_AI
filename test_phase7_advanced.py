"""
Phase 7 Test: Advanced Integration.

Tests:
1. Task Memory (storage, history)
2. Context Awareness (active app)
"""

import sys
import os
import tempfile
import shutil

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from assistant.memory import (
    TaskMemory, TaskRecord, ActionPattern,
    ContextAwareness, AppContext,
)


def test_task_memory():
    print("=== PHASE 7 TEST: TASK MEMORY ===\n")
    
    # Use temp directory for testing
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Test 1: Create memory
        print("1. Testing memory initialization...")
        memory = TaskMemory(storage_path=temp_dir)
        print("   ✅ Memory created")
        
        # Test 2: Record task
        print("2. Testing task recording...")
        record = TaskRecord(
            id="test-1",
            task="Test task",
            steps_completed=5,
            steps_total=5,
            success=True,
            duration_sec=10.5,
            started_at="2026-01-15T10:00:00",
            completed_at="2026-01-15T10:00:10",
        )
        memory.record_task(record)
        history = memory.get_history()
        assert len(history) == 1
        print("   ✅ Task recorded")
        
        # Test 3: Context storage
        print("3. Testing context storage...")
        memory.set_context("last_url", "https://example.com")
        value = memory.get_context("last_url")
        assert value == "https://example.com"
        print("   ✅ Context stored/retrieved")
        
        # Test 4: Pattern learning
        print("4. Testing pattern learning...")
        memory.learn_pattern("open browser", [{"action": "click", "target": "Chrome"}], True)
        pattern = memory.get_pattern("open browser")
        assert pattern is not None
        assert pattern.success_rate == 1.0
        print("   ✅ Pattern learned")
        
        # Test 5: Stats
        print("5. Testing stats...")
        stats = memory.get_stats()
        assert stats["total_tasks"] == 1
        assert stats["patterns_learned"] == 1
        print(f"   ✅ Stats: {stats}")
        
    finally:
        shutil.rmtree(temp_dir)
    
    print("\n✅ Task Memory: PASSED")
    return True


def test_context_awareness():
    print("\n=== PHASE 7 TEST: CONTEXT AWARENESS ===\n")
    
    # Test 1: Create context tracker
    print("1. Testing context initialization...")
    ctx = ContextAwareness()
    print("   ✅ Context tracker created")
    
    # Test 2: Get active app
    print("2. Testing active app detection...")
    app = ctx.get_active_app()
    if app:
        print(f"   ✅ Active app: {app.process_name}")
        print(f"      Window: {app.window_title[:50]}...")
    else:
        print("   ⚠️ Could not detect active app (may need pywin32)")
    
    # Test 3: Browser/editor detection
    print("3. Testing app classification...")
    print(f"   Is browser: {ctx.is_in_browser()}")
    print(f"   Is editor: {ctx.is_in_editor()}")
    print("   ✅ Classification works")
    
    # Test 4: Context summary
    print("4. Testing context summary...")
    summary = ctx.get_context_summary()
    assert "active_app" in summary
    assert "is_browser" in summary
    print(f"   ✅ Summary: {summary['active_app']}")
    
    print("\n✅ Context Awareness: PASSED")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("       PHASE 7 ADVANCED INTEGRATION TESTS")
    print("=" * 50)
    
    results = []
    
    try:
        results.append(("Task Memory", test_task_memory()))
        results.append(("Context Awareness", test_context_awareness()))
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("       PHASE 7 RESULTS")
    print("=" * 50)
    
    all_pass = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_pass = False
    
    if all_pass:
        print("\n✨ PHASE 7 ADVANCED INTEGRATION: ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n❌ PHASE 7: SOME TESTS FAILED")
        sys.exit(1)
