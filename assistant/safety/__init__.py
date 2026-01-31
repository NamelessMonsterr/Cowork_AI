"""Safety and permission management modules."""

from .budget import ActionBudget, BudgetExceededError
from .environment import EnvironmentMonitor, EnvironmentState
from .plan_guard import PlanGuard, PlanValidationError
from .sensitive_detector import SensitiveDetection, SensitiveDetector, SensitiveType
from .session_auth import SessionAuth, SessionPermit
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
