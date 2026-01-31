"""
Recovery Context - Snapshot for Repair Planner (W9.2).
"""

from dataclasses import dataclass
from typing import List, Optional, Any, Dict
from assistant.ui_contracts.schemas import ActionStep, StepResult
from assistant.recovery.classifier import FailureType


@dataclass
class RecoveryContext:
    plan_id: str
    step_id: str
    task: str
    failure_type: FailureType
    active_window: str
    process_name: str
    failed_step: ActionStep
    step_result: StepResult
    recent_steps: List[ActionStep]
    # Detailed Context
    screenshot_before_b64: Optional[str] = None
    uia_tree: Optional[Dict[str, Any]] = None

    def to_prompt_context(self) -> str:
        """Serialize relevant info for the Planner."""
        return f"""
        Failed Step: {self.failed_step.tool} {self.failed_step.args}
        Error: {self.step_result.error}
        Failure Type: {self.failure_type.value}
        Active Window: {self.active_window} (Process: {self.process_name})
        Recent Steps: {[s.tool for s in self.recent_steps[-3:]]}
        """
