"""Safety and permission management modules."""

from .session_auth import SessionAuth, SessionPermit
from .plan_guard import PlanGuard, PlanValidationError
from .environment import EnvironmentMonitor, EnvironmentState
from .budget import ActionBudget, BudgetExceededError
from .sensitive_detector import SensitiveDetector, SensitiveType, SensitiveDetection
from .takeover import TakeoverManager, TakeoverReason, TakeoverState

__all__ = [
    "SessionAuth",
    "SessionPermit",
    "PlanGuard",
    "PlanValidationError",
    "EnvironmentMonitor",
    "EnvironmentState",
    "ActionBudget",
    "BudgetExceededError",
    "SensitiveDetector",
    "SensitiveType",
    "SensitiveDetection",
    "TakeoverManager",
    "TakeoverReason",
    "TakeoverState",
]
