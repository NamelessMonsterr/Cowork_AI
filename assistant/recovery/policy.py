"""
Recovery Policy - Limits and Rules (W9.5).
"""

from dataclasses import dataclass
from assistant.recovery.classifier import FailureType

@dataclass
class RecoveryPolicy:
    max_attempts_per_step: int = 2
    max_total_attempts: int = 5
    max_repair_steps: int = 5 # Per repair plan
    max_repair_time_sec: int = 30
    
    def can_recover(self, failure_type: FailureType, current_attempts: int) -> bool:
        """Check if recovery is allowed."""
        
        # Hard Safety Rules
        if failure_type in [
            FailureType.BLOCKED_BY_UAC, 
            FailureType.SENSITIVE_SCREEN,
            FailureType.PERMISSION_REQUIRED
        ]:
            return False
            
        # Limits
        if current_attempts >= self.max_attempts_per_step:
            return False
            
        return True
