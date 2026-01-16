"""
Benchmark Harness - Connects Benchmark Runner to Real Executor (W11.3).

Responsibilities:
1. Initialize Executor stack (Computer, Verifier, Recovery).
2. Convert Task Config to ExecutionPlan.
3. Execute Plan safely.
4. Capture precise latency and success/fail metrics.
"""

import time
import uuid
import logging
from typing import Dict, Any, Optional

from assistant.computer.windows import WindowsComputer
from assistant.executor.executor import ReliableExecutor
from assistant.executor.verify import Verifier
from assistant.executor.strategies import UIAStrategy, VisionStrategy, CoordsStrategy
from assistant.recovery.manager import RecoveryManager
from assistant.safety.plan_guard import PlanGuard, ExecutionPlan
from assistant.safety.budget import ActionBudget
from assistant.safety.environment import EnvironmentMonitor
from assistant.session_auth import SessionAuth
from assistant.recorder.context import ContextTracker
from assistant.agent.planner import Planner 
from assistant.ui_contracts.schemas import ActionStep

logger = logging.getLogger("BenchmarkHarness")

class TaskHarness:
    def __init__(self):
        # Initialize Core Stack (Mocking Main.py lifespan logic)
        self.computer = WindowsComputer()
        
        # We need a SessionAuth wrapper that respects Benchmark Mode
        self.session_auth = SessionAuth() 
        # Note: BenchmarkRunner enfores Mode + Session at start.
        
        self.environment = EnvironmentMonitor(on_unsafe=self._on_unsafe)
        self.budget = ActionBudget(max_actions=50) # Strict budget for benchmarks
        
        strategies = [UIAStrategy(), VisionStrategy(), CoordsStrategy()]
        self.verifier = Verifier(self.computer, strategies)
        
        self.executor = ReliableExecutor(
            strategies=strategies,
            verifier=self.verifier,
            session_auth=self.session_auth,
            budget=self.budget,
            environment=self.environment
        )
        
        self.planner = Planner(self.computer)
        self.plan_guard = PlanGuard(self.session_auth)
        
        self.recovery_manager = RecoveryManager(
            planner=self.planner,
            executor=self.executor,
            plan_guard=self.plan_guard,
            computer=self.computer
        )
        
    def _on_unsafe(self, state, reason):
        logger.error(f"BENCHMARK UNSAFE: {reason}")
        # In benchmark, we abort immediately
        raise RuntimeError(f"Unsafe Environment: {reason}")
        
    async def execute(self, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a benchmark task.
        Returns: {success: bool, steps_total: int, steps_completed: int, error: str, duration: float}
        """
        start_time = time.time()
        
        try:
            # 1. Plan Generation (Or Static Loading)
            # Benchmarks usually have static steps for determinism.
            raw_steps = task_config.get('steps', [])
            action_steps = [ActionStep(**s) for s in raw_steps]
            
            # Ensure IDs
            for i, s in enumerate(action_steps):
                if not s.id: s.id = str(i+1)
                
            plan = ExecutionPlan(
                id=str(uuid.uuid4()),
                task=task_config.get('task', 'Benchmark Task'),
                steps=action_steps
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
                        recent_steps=recent_steps
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
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Task Failed: {e}")
            return {
                "success": False,
                "steps_total": len(raw_steps) if 'raw_steps' in locals() else 0,
                "steps_completed": steps_completed if 'steps_completed' in locals() else 0,
                "duration": time.time() - start_time,
                "error": str(e)
            }
