"""
Benchmark Harness - Connects Benchmark Runner to Real Executor (W11.3).

Responsibilities:
1. Initialize Executor stack (Computer, Verifier, Recovery).
2. Convert Task Config to ExecutionPlan.
3. Execute Plan safely.
4. Capture precise latency and success/fail metrics.
"""

import logging
import time
import uuid
from typing import Any

from assistant.agent.planner import Planner
from assistant.computer.windows import WindowsComputer
from assistant.executor.executor import ReliableExecutor
from assistant.executor.strategies import CoordsStrategy, UIAStrategy, VisionStrategy
from assistant.executor.verify import Verifier
from assistant.recovery.manager import RecoveryManager
from assistant.safety.budget import ActionBudget, BudgetConfig
from assistant.safety.environment import EnvironmentMonitor
from assistant.safety.plan_guard import ExecutionPlan, PlanGuard, PlanGuardConfig
from assistant.session_auth import SessionAuth
from assistant.ui_contracts.schemas import ActionStep

logger = logging.getLogger("BenchmarkHarness")


class TaskHarness:
    def __init__(self):
        # Initialize Core Stack (Mocking Main.py lifespan logic)
        self.computer = WindowsComputer()

        # We need a SessionAuth wrapper that respects Benchmark Mode
        self.session_auth = SessionAuth()
        # Grant all permissions for benchmark
        self.session_auth.grant(apps=["*"], folders=["*"], mode="session")

        # Note: BenchmarkRunner enfores Mode + Session at start.

        self.environment = EnvironmentMonitor(on_unsafe=self._on_unsafe)
        self.budget = ActionBudget(config=BudgetConfig(max_actions_per_task=50))  # Strict budget for benchmarks

        # Import SystemStrategy from production module (same as main.py)
        from assistant.executor.strategies.system import SystemStrategy

        strategies = [
            SystemStrategy(self.computer),
            UIAStrategy(),
            VisionStrategy(),
            CoordsStrategy(),
        ]
        self.verifier = Verifier(self.computer, strategies)

        self.executor = ReliableExecutor(
            strategies=strategies,
            verifier=self.verifier,
            session_auth=self.session_auth,
            budget=self.budget,
            environment=self.environment,
        )

        self.planner = Planner(self.computer)
        self.plan_guard = PlanGuard(self.session_auth, config=PlanGuardConfig(require_verification=False))

        self.recovery_manager = RecoveryManager(
            planner=self.planner,
            executor=self.executor,
            plan_guard=self.plan_guard,
            computer=self.computer,
        )

    def _on_unsafe(self, state, reason):
        logger.error(f"BENCHMARK UNSAFE: {reason}")
        # In benchmark, we abort immediately
        raise RuntimeError(f"Unsafe Environment: {reason}")

    async def execute(self, task_config: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a benchmark task.
        Returns: {success: bool, steps_total: int, steps_completed: int, error: str, duration: float}
        """
        start_time = time.time()

        try:
            # 1. Plan Generation (Or Static Loading)
            # Benchmarks usually have static steps for determinism.
            # 1. Plan Generation (Or Static Loading)
            raw_steps = task_config.get("steps", [])
            action_steps = []

            # Global verification spec for the task
            verify_config = task_config.get("verification")
            verify_spec = None
            if verify_config:
                # Map YAML fields to VerifySpec
                v_type = verify_config.get("type")
                v_value = (
                    verify_config.get("contains")
                    or verify_config.get("text")
                    or verify_config.get("path")
                    or verify_config.get("name")
                    or ""
                )
                from assistant.ui_contracts.schemas import VerifySpec

                try:
                    verify_spec = VerifySpec(
                        type=v_type,
                        value=v_value,
                        timeout=verify_config.get("timeout", 5),
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse verify spec: {e}")

            for i, s in enumerate(raw_steps):
                # Map 'action' to 'tool'
                tool = s.pop("action", None)
                if not tool:
                    # Fallback if 'tool' key exists
                    tool = s.pop("tool", "unknown")

                # Map 'run' to 'open_app' (standard schema)
                if tool == "run":
                    tool = "open_app"
                    # Map 'command' to 'app_name' if needed, but executor probably expects app_name or command
                    if "command" in s:
                        s["app_name"] = s.pop("command")

                step_id = s.pop("id", str(i + 1))

                # Extract known fields for ActionStep
                known_fields = [
                    "timeout",
                    "retries",
                    "risk_level",
                    "verify",
                    "unverifiable",
                    "description",
                ]
                step_kwargs = {k: s.pop(k) for k in known_fields if k in s}

                # Remaining items are args for the tool
                args = s.copy()

                # Attach verification to the LAST step if not present
                if i == len(raw_steps) - 1 and verify_spec and not step_kwargs.get("verify"):
                    step_kwargs["verify"] = verify_spec

                step = ActionStep(id=step_id, tool=tool, args=args, **step_kwargs)
                action_steps.append(step)

            # Ensure IDs
            for i, s in enumerate(action_steps):
                if not s.id:
                    s.id = str(i + 1)

            plan = ExecutionPlan(
                id=str(uuid.uuid4()),
                task=task_config.get("task", "Benchmark Task"),
                steps=action_steps,
            )

            # 2. Guard
            self.plan_guard.validate(plan)

            # 3. Execution Loop (with Recovery)
            steps_completed = 0

            for i, step in enumerate(plan.steps):
                # Execute
                result = self.executor.execute(step)

                if not result.success:
                    # Try Recovery
                    logger.warning(f"Step {step.id} Failed. Attempting Benchmark Recovery...")

                    recent_steps = plan.steps[:i]
                    recovered = await self.recovery_manager.handle_failure(
                        plan_id=plan.id,
                        failed_step=step,
                        step_result=result,
                        recent_steps=recent_steps,
                    )

                    if recovered:
                        retry_res = self.executor.execute(step)
                        if not retry_res.success:
                            raise RuntimeError(f"Step {step.id} failed after recovery: {retry_res.error}")
                    else:
                        raise RuntimeError(f"Step {step.id} failed and not recovered: {result.error}")

                steps_completed += 1

            return {
                "success": True,
                "steps_total": len(plan.steps),
                "steps_completed": steps_completed,
                "duration": time.time() - start_time,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Task Failed: {e}")
            return {
                "success": False,
                "steps_total": len(raw_steps) if "raw_steps" in locals() else 0,
                "steps_completed": steps_completed if "steps_completed" in locals() else 0,
                "duration": time.time() - start_time,
                "error": str(e),
            }
