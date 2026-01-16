"""
Plan Guard - Pre-flight validation for execution plans.

Validates plans before execution to catch:
- Too many steps (runaway prevention)
- High-risk actions without approval
- Unknown tools
- Actions outside allowed apps/folders
- Network access without permission
"""

from typing import Optional, Set
from dataclasses import dataclass
from pydantic import BaseModel

from .session_auth import SessionAuth


class PlanValidationError(Exception):
    """Raised when plan validation fails."""
    
    def __init__(self, message: str, violations: list[str]):
        super().__init__(message)
        self.violations = violations


@dataclass
class PlanGuardConfig:
    """Configuration for plan validation."""
    max_steps: int = 25
    max_high_risk_steps: int = 0  # By default, block all high-risk
    max_retries_total: int = 20
    require_verification: bool = True  # Each step must have verify OR marked unverifiable
    allowed_tools: Optional[Set[str]] = None  # None = allow all known tools
    blocked_domains: Set[str] = None
    
    def __post_init__(self):
        if self.blocked_domains is None:
            self.blocked_domains = {
                "*.exe",  # Direct executables
                "registry",  # Registry modifications
                "admin",  # Admin operations
            }


# Known safe tools that the executor supports
KNOWN_TOOLS = {
    # Mouse actions
    "click", "double_click", "right_click", "scroll", "move", "drag",
    # Keyboard actions
    "type", "keypress",
    # Window actions
    "focus_window", "open_app", "get_active_window",
    # Navigation (for browser contexts)
    "navigate", "goto", "back", "forward",
    # Utility
    "wait", "screenshot",
    # File operations (restricted)
    "save_file", "open_file", "download",
}

# Tools that require extra scrutiny
HIGH_RISK_TOOLS = {
    "keypress",  # Could be ctrl+alt+del, etc.
    "open_app",  # Could open anything
    "download",  # Downloads files
}


class PlanGuard:
    """
    Pre-flight validator for execution plans.
    
    Usage:
        guard = PlanGuard(session_auth, config)
        
        try:
            guard.validate(plan)
        except PlanValidationError as e:
            print(f"Plan rejected: {e.violations}")
    """

    def __init__(
        self,
        session_auth: SessionAuth,
        config: Optional[PlanGuardConfig] = None,
    ):
        """
        Initialize PlanGuard.
        
        Args:
            session_auth: Session auth for permission checking
            config: Validation configuration
        """
        self._session = session_auth
        self._config = config or PlanGuardConfig()

    def validate(self, plan: "ExecutionPlan", allow_high_risk: bool = False) -> None:
        """
        Validate an execution plan.
        
        Args:
            plan: The plan to validate
            allow_high_risk: If True, allow high-risk steps (requires explicit user approval)
            
        Raises:
            PlanValidationError: If validation fails
        """
        violations: list[str] = []
        
        # 1. Check step count
        if len(plan.steps) > self._config.max_steps:
            violations.append(
                f"Plan has {len(plan.steps)} steps, max allowed is {self._config.max_steps}"
            )
        
        # 2. Count risk levels and check tools
        high_risk_count = 0
        total_retries = 0
        
        for i, step in enumerate(plan.steps):
            step_num = i + 1
            
            # Check tool is known
            if step.tool not in KNOWN_TOOLS:
                if self._config.allowed_tools and step.tool not in self._config.allowed_tools:
                    violations.append(f"Step {step_num}: Unknown tool '{step.tool}'")
            
            # Check risk level
            if step.risk_level == "high":
                high_risk_count += 1
                if step.tool in HIGH_RISK_TOOLS:
                    # Check specific high-risk patterns
                    self._check_high_risk_step(step, step_num, violations)
            
            # Count retries
            total_retries += step.retries
            
            # Check verification requirement
            if self._config.require_verification:
                if step.verify is None and not getattr(step, 'unverifiable', False):
                    violations.append(
                        f"Step {step_num}: Missing verification spec (add verify or mark as unverifiable)"
                    )
            
            # Check app permissions
            if step.tool == "open_app":
                app_name = step.args.get("app_name", "")
                if not self._session.is_app_allowed(app_name):
                    violations.append(
                        f"Step {step_num}: App '{app_name}' is not in allowed list"
                    )
            
            # Check folder permissions for file operations
            if step.tool in ("save_file", "open_file"):
                path = step.args.get("path", "")
                if not self._session.is_folder_allowed(path):
                    violations.append(
                        f"Step {step_num}: Path '{path}' is not in allowed folders"
                    )
        
        # 3. Check high-risk count
        max_high_risk = self._config.max_high_risk_steps if not allow_high_risk else 999
        if high_risk_count > max_high_risk:
            violations.append(
                f"Plan has {high_risk_count} high-risk steps, max allowed is {max_high_risk} "
                "(requires explicit approval)"
            )
        
        # 4. Check total retries
        if total_retries > self._config.max_retries_total:
            violations.append(
                f"Plan allows {total_retries} total retries, max allowed is {self._config.max_retries_total}"
            )
        
        # 5. Check network requirement
        if plan.requires_network and not self._session.is_network_allowed():
            violations.append("Plan requires network access but session does not permit it")
        
        # 6. Check admin requirement
        if plan.requires_admin:
            violations.append("Plan requires admin privileges which are not supported")
        
        if violations:
            raise PlanValidationError(
                f"Plan validation failed with {len(violations)} violation(s)",
                violations
            )

    def _check_high_risk_step(
        self, 
        step: "ActionStep", 
        step_num: int, 
        violations: list[str]
    ) -> None:
        """Check high-risk step for dangerous patterns."""
        
        if step.tool == "keypress":
            keys = step.args.get("keys", [])
            keys_lower = [k.lower() for k in keys]
            
            # Block dangerous key combinations
            dangerous_combos = [
                ({"ctrl", "alt", "delete"}, "Ctrl+Alt+Delete"),
                ({"alt", "f4"}, "Alt+F4 (close window)"),
                ({"win", "l"}, "Win+L (lock screen)"),
                ({"win", "r"}, "Win+R (run dialog)"),
            ]
            
            for combo, name in dangerous_combos:
                if combo.issubset(set(keys_lower)):
                    violations.append(
                        f"Step {step_num}: Blocked dangerous keypress {name}"
                    )
        
        elif step.tool == "open_app":
            app_name = step.args.get("app_name", "").lower()
            
            # Block potentially dangerous apps
            blocked_apps = {
                "regedit", "cmd", "powershell", "wt", 
                "taskmgr", "mmc", "gpedit",
            }
            
            if app_name in blocked_apps:
                violations.append(
                    f"Step {step_num}: App '{app_name}' is blocked for safety"
                )

    def get_risk_summary(self, plan: "ExecutionPlan") -> dict:
        """
        Get a risk summary for UI display.
        
        Returns:
            Dictionary with risk metrics
        """
        risk_counts = {"low": 0, "medium": 0, "high": 0}
        tools_used = set()
        
        for step in plan.steps:
            risk_counts[step.risk_level] += 1
            tools_used.add(step.tool)
        
        return {
            "total_steps": len(plan.steps),
            "risk_counts": risk_counts,
            "tools_used": list(tools_used),
            "requires_network": plan.requires_network,
            "requires_admin": plan.requires_admin,
            "estimated_time_sec": plan.estimated_time_sec,
            "has_high_risk": risk_counts["high"] > 0,
        }


# Type hints for plan objects (will be fully defined in ui_contracts)
class ActionStep(BaseModel):
    """Placeholder - full definition in ui_contracts/schemas.py"""
    tool: str
    args: dict = {}
    verify: Optional[dict] = None
    timeout: int = 10
    retries: int = 3
    risk_level: str = "low"


class ExecutionPlan(BaseModel):
    """Placeholder - full definition in ui_contracts/schemas.py"""
    task: str
    steps: list[ActionStep]
    estimated_time_sec: int = 0
    requires_network: bool = False
    requires_admin: bool = False
