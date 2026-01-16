"""
W15 Verification - Destructive Guardrails.
"""
import sys
import os
sys.path.append(os.getcwd())

from assistant.ui_contracts.schemas import ExecutionPlan, ActionStep
from assistant.safety.destructive_guard import DestructiveGuard

def test_destructive_guard():
    print("🧪 Testing Destructive Guard...")
    guard = DestructiveGuard()

    # 1. Safe Plan
    safe_plan = ExecutionPlan(
        id="safe",
        task="list files",
        steps=[ActionStep(id="1", tool="run_command", args={"command": "dir"}, description="list")]
    )
    try:
        guard.validate(safe_plan)
        print("✅ Safe plan allowed.")
    except Exception as e:
        print(f"❌ Safe plan blocked: {e}")

    # 2. Unsafe Plan (rm -rf)
    unsafe_plan = ExecutionPlan(
        id="unsafe",
        task="nuke",
        steps=[ActionStep(id="1", tool="run_command", args={"command": "rm -rf /"}, description="nuke")]
    )
    try:
        guard.validate(unsafe_plan)
        print("❌ Unsafe plan allowed!")
    except ValueError as e:
        print(f"✅ Unsafe plan blocked: {e}")

    # 3. Wildcard Delete
    wildcard_plan = ExecutionPlan(
        id="wild",
        task="del all",
        steps=[ActionStep(id="1", tool="run_command", args={"command": "del *.txt"}, description="del tree")]
    )
    try:
        guard.validate(wildcard_plan)
        print("❌ Wildcard plan allowed!")
    except ValueError as e:
        print(f"✅ Wildcard plan blocked: {e}")

if __name__ == "__main__":
    test_destructive_guard()
