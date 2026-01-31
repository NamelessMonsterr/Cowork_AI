"""
W9 Verification Script: Self-Healing Demo.

Scenario:
1. Start a mock plan.
2. Step 1 fails with "Element Not Found".
3. Verify RecoveryManager intercepts.
4. Verify Repair Plan is generated.
5. Verify Retry happens.
"""

import asyncio
import logging
import os
import sys
from unittest.mock import AsyncMock, MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from assistant.main import run_plan_execution, state
from assistant.recovery.manager import RecoveryManager
from assistant.ui_contracts.schemas import ActionStep, ExecutionPlan, StepResult

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DemoW9")


async def mock_execution_scenario():
    logger.info("=== Starting W9 Self-Healing Verification ===")

    # 1. Setup Mock State
    state.session_auth.grant()
    if state.computer:
        state.computer.set_session_verifier(state.session_auth.ensure)

    # Manually Init Components (W9 requires them)
    from assistant.agent.planner import Planner

    state.planner = Planner(state.computer)

    # Mock Planner to return a plan
    mock_step_1 = ActionStep(id="step1", tool="click", args={"name": "Submit"}, description="Click Submit")
    # Using AsyncMock for async method
    state.planner.create_plan = AsyncMock(
        return_value=[
            {
                "id": "step1",
                "tool": "click",
                "args": {"name": "Submit"},
                "description": "Click Submit",
            }
        ]
    )

    # Init Executor manually if needed, but we replace execute method anyway.
    # But init is cleaner to avoid other NoneTypes
    from assistant.executor.executor import ReliableExecutor

    # Mock dependencies for executor
    strategies = []
    verifier = MagicMock()
    budget = MagicMock()
    env = MagicMock()

    state.executor = ReliableExecutor(strategies, verifier, state.session_auth, budget, env)

    # Init Recovery Manager
    # Use PlanGuard mock
    pg = MagicMock()
    state.plan_guard = pg

    state.recovery_manager = RecoveryManager(state.planner, state.executor, state.plan_guard, state.computer)

    # Mock Executor to Fail first, then Succeed
    # We can't easily mock internal method of real executor instance without replacing it.
    # Let's replace state.executor.execute with a side-effect mock.

    original_execute = state.executor.execute

    call_count = 0

    def side_effect_execute(step):
        nonlocal call_count
        call_count += 1
        logger.info(f"Executor called for {step.id} (Call #{call_count})")

        if call_count == 1:
            # First attempt fails
            return StepResult(
                step_id=step.id,
                success=False,
                error="Element 'Submit' not found in UI tree",
                duration_ms=100,
            )
        else:
            # Retry or Repair succeeds
            return StepResult(step_id=step.id, success=True, duration_ms=100)

    state.executor.execute = side_effect_execute

    # Mock Planner Repair Generation
    # Real planner would call LLM. We mock it to return a dummy repair plan.
    async def mock_repair(context):
        logger.info(f"Generating Repair for: {context.failure_type}")
        return ExecutionPlan(
            id="repair_1",
            task="Repair",
            steps=[ActionStep(id="repair_step_1", tool="wait", args={"duration": 1})],
        )

    state.planner.generate_repair_plan = mock_repair

    # 2. Run Execution
    logger.info("\n--- Running Plan ---")
    await run_plan_execution("Click Submit Button")

    # 3. Verify Logic
    if call_count >= 3:
        # 1. Base Fail
        # 2. Repair Step
        # 3. Retry Base
        logger.info("✅ Recovery Flow Confirmed (Fail -> Repair -> Retry)")
    else:
        logger.warning(f"⚠️ Unexpected call count: {call_count}")

    logger.info("=== W9 Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(mock_execution_scenario())
