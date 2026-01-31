"""
Recovery Manager - Orchestrates Self-Healing Loop (W9.1).

Coordinates: Executor <-> Classifier <-> Planner (Repair)
"""

import asyncio
import logging

from assistant.recovery.classifier import FailureClassifier
from assistant.recovery.context import RecoveryContext
from assistant.recovery.policy import RecoveryPolicy
from assistant.ui_contracts.schemas import ActionStep, StepResult

logger = logging.getLogger("RecoveryManager")


class RecoveryManager:
    def __init__(
        self,
        planner: "Planner",
        executor: "ReliableExecutor",
        plan_guard: "PlanGuard",
        computer: "WindowsComputer",
    ):
        self.planner = planner
        self.executor = executor
        self.plan_guard = plan_guard
        self.computer = computer

        self.policy = RecoveryPolicy()
        self.classifier = FailureClassifier()

        # State tracking: plan_id -> step_id -> attempt_count
        self._attempts: dict[str, dict[str, int]] = {}

    async def handle_failure(
        self,
        plan_id: str,
        failed_step: ActionStep,
        step_result: StepResult,
        recent_steps: list,
    ) -> bool:
        """
        Attempt to recover from a step failure.
        Returns True if recovery succeeded (original step should be retried).
        Returns False if recovery failed or not allowed.
        """
        # 1. Track Attempts
        if plan_id not in self._attempts:
            self._attempts[plan_id] = {}
        current_attempts = self._attempts[plan_id].get(failed_step.id, 0)

        # 2. Classify
        f_type, recoverable = self.classifier.classify(step_result.error or "")

        # 3. Check Policy
        if not recoverable:
            logger.warning(f"Failure not recoverable: {f_type}")
            return False

        if not self.policy.can_recover(f_type, current_attempts):
            logger.warning(f"Recovery limits exceeded for {failed_step.id} (Type: {f_type})")
            return False

        # 4. Prepare Context
        win_info = self.computer.get_active_window()
        context = RecoveryContext(
            plan_id=plan_id,
            step_id=failed_step.id,
            task="Unknown",  # Passed from caller usually
            failure_type=f_type,
            active_window=win_info.title if win_info else "Unknown",
            process_name="Unknown",  # Need PID resolution
            failed_step=failed_step,
            step_result=step_result,
            recent_steps=recent_steps,
            # TODO: Add screenshots
        )

        logger.info(f"Starting Recovery for {failed_step.id} (Attempt {current_attempts + 1})...")

        try:
            # 5. Generate Repair Plan
            repair_plan = await self.planner.generate_repair_plan(context)

            # 6. Validate Repair Plan (Safety)
            self.plan_guard.validate(repair_plan)

            # 7. Execute Repair Plan
            # Should we broadcast events? Yes, caller handles or we inject?
            # Ideally manager calls broadcast, but we need reference.
            # Simplified: Just execute steps.

            success = True
            for step in repair_plan.steps:
                res = await asyncio.to_thread(self.executor.execute, step)
                if not res.success:
                    logger.error(f"Repair step failed: {step.id} - {res.error}")
                    success = False
                    break

            if success:
                self._attempts[plan_id][failed_step.id] = current_attempts + 1
                logger.info("Recovery actions succeeded. Retrying original step.")
                return True

        except Exception as e:
            logger.error(f"Recovery failed: {e}")

        return False
