"""
Plan Guard - Pre-flight validation for execution plans.

Validates plans before execution to catch:
- Too many steps (runaway prevention)
- High-risk actions without approval
- Unknown tools (default-deny policy)
- Actions outside allowed apps/folders
- Network access without permission
- Destructive operations (drag, file ops, clipboard)
"""

import json
import logging
from typing import Optional, Set
from dataclasses import dataclass
from pathlib import Path
from pydantic import BaseModel

from .session_auth import SessionAuth
from assistant.ui_contracts.schemas import ExecutionPlan, ActionStep
from assistant.safety.destructive_guard import DestructiveGuard

logger = logging.getLogger(__name__)


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


# HARDENED SECURITY POLICY

# Task 3: Removed 'drag' from SAFE_TOOLS (destructive risk)
# Safe tools - always allowed, no additional validation
SAFE_TOOLS = {
    # Mouse actions (drag REMOVED - can delete files, leak data)
    "click", "double_click", "right_click", "scroll", "move",
    # Keyboard actions (keypress validated for dangerous combos)
    "type", "type_text", "keypress",
    # Window actions
    "focus_window", "get_active_window",
    # Utility
    "wait", "screenshot"
}

# Restricted but safe tools - require allowlist validation
RESTRICTED_SAFE_TOOLS = {
    "open_app",  # Safe if app in TRUSTED_APPS
    "open_url",  # Safe if domain in TRUSTED_DOMAINS
    "restricted_shell"  # Safe if command in ALLOWED_COMMANDS
}

# Task 5: Expanded blocklist - indirect attack vectors
BLOCKED_TOOLS = {
    # Shell/command execution
    "run_shell", "shell", "cmd", "powershell", "bash",
    "run_command", "exec", "eval",
    
    # File system operations (indirect attack vectors)
    "delete_file", "write_file", "read_file", "list_dir",
    "upload_file", "download",
    
    # Clipboard (data leakage risk)
    "clipboard_get", "clipboard_set",
    
    # System modification
    "registry_edit", "set_env", "install",
    
    # File operations that were in RESTRICTED (now blocked)
    "open_file", "save_file"
}

# Task 1: Fallback trusted apps (config-driven preferred)
TRUSTED_APPS_DEFAULT = {
    "notepad", "notepad.exe",
    "calc", "calc.exe", "calculator", "calculator.exe",
    "mspaint", "mspaint.exe", "paint",
    "wordpad", "wordpad.exe"
}

# Task 4: All known tools for default-deny validation
ALL_KNOWN_TOOLS = SAFE_TOOLS | RESTRICTED_SAFE_TOOLS | BLOCKED_TOOLS

# Legacy high-risk tools list (mostly replaced by allowlists)
HIGH_RISK_TOOLS = {
    "keypress",  # Validated for dangerous key combinations
}


# Task 1: Load trusted apps from config
def load_trusted_apps() -> tuple[set, dict]:
    """
    Load trusted apps from config file with fallback to defaults.
    Returns: (trusted_apps_set, app_aliases_dict)
    """
    try:
        config_path = Path(__file__).parent.parent / "config" / "trusted_apps.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                data = json.load(f)
            trusted = set(data.get("trusted_apps", []))
            aliases = data.get("app_aliases", {})
            logger.info(f"[PlanGuard] Loaded {len(trusted)} trusted apps from config")
            return trusted, aliases
    except Exception as e:
        logger.warning(f"[PlanGuard] Failed to load config: {e}, using defaults")
    
    return TRUSTED_APPS_DEFAULT, {}


def load_trusted_domains() -> set:
    """
    Load trusted domains from config with fallback to defaults.
    Returns: set of trusted domain strings
    """
    try:
        config_path = Path(__file__).parent.parent / "config" / "trusted_domains.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                data = json.load(f)
            domains = set(data.get("trusted_domains", []))
            logger.info(f"[PlanGuard] Loaded {len(domains)} trusted domains from config")
            return domains
    except Exception as e:
        logger.warning(f"[PlanGuard] Failed to load domains: {e}, using defaults")
    
    return {"github.com", "google.com", "openai.com", "microsoft.com"}


def load_restricted_shell_config() -> dict:
    """
    Load restricted shell configuration.
    Returns: config dict with enabled flag and allowlists
    """
    try:
        config_path = Path(__file__).parent.parent / "config" / "restricted_shell.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            cmd_count = len(config.get("allowed_cmd", []))
            ps_count = len(config.get("allowed_powershell", []))
            logger.info(f"[PlanGuard] Loaded RestrictedShell config: {cmd_count} cmd, {ps_count} powershell")
            return config
    except Exception as e:
        logger.warning(f"[PlanGuard] Failed to load restricted shell config: {e}")
    
    return {"enabled": False}


# Task 2: Normalize app names for path handling
def normalize_app_name(app: str) -> tuple[str, str]:
    """
    Normalize app name handling full paths, case, and whitespace.
    
    Examples:
        "C:\\Windows\\System32\\notepad.exe" → ("notepad.exe", "notepad")
        "NOTEPAD.EXE " → ("notepad.exe", "notepad")
        "calculator" → ("calculator", "calculator")
    
    Returns:
        (exe_name, exe_no_ext)
    """
    raw = str(app).strip().lower()
    exe_name = Path(raw).name  # Extracts filename from path
    exe_no_ext = exe_name.removesuffix(".exe")
    return exe_name, exe_no_ext


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
        self.destructive_guard = DestructiveGuard()
        
        # Task 1: Load config-driven trusted apps and domains
        self.trusted_apps, self.app_aliases = load_trusted_apps()
        self.trusted_domains = load_trusted_domains()
        self.restricted_shell_config = load_restricted_shell_config()

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

        # 0. W15.2 Destructive Actions Check
        try:
            self.destructive_guard.validate(plan)
        except ValueError as e:
            violations.append(str(e))
        
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
            
            # Task 4: Default-deny - Check if tool is recognized
            if step.tool not in ALL_KNOWN_TOOLS:
                # Special case: plugin tools
                if step.tool.startswith("plugin:"):
                    violations.append(
                        f"Step {step_num}: Plugin tools require explicit permission"
                    )
                else:
                    violations.append(
                        f"Step {step_num}: Tool '{step.tool}' is not recognized. "
                        f"Allowed tools: {', '.join(sorted(SAFE_TOOLS | RESTRICTED_SAFE_TOOLS))}"
                    )
                continue
            
            # Block dangerous tools
            if step.tool in BLOCKED_TOOLS:
                violations.append(
                    f"Step {step_num}: Tool '{step.tool}' is blocked for safety"
                )
                continue
            
            # Allow safe tools with minimal checks
            if step.tool in SAFE_TOOLS:
                # Still check for dangerous keypress combinations
                if step.tool == "keypress":
                    self._check_dangerous_keypress(step, step_num, violations)
                # Count retries
                total_retries += step.retries
                continue
            
            # Task 2: Validate restricted tools with normalization
            if step.tool == "open_app":
                app_raw = step.args.get("app_name", "") or step.args.get("name", "")
                if not app_raw:
                    violations.append(f"Step {step_num}: open_app missing app_name argument")
                    continue
                
                # Normalize: handle paths, case, whitespace
                exe_name, exe_no_ext = normalize_app_name(app_raw)
                
                # Check aliases
                resolved_name = self.app_aliases.get(exe_no_ext, exe_no_ext)
                
                # Allow if in trusted list (either full name or no-ext)
                is_trusted = (
                    exe_name in self.trusted_apps or
                    exe_no_ext in self.trusted_apps or
                    resolved_name in self.trusted_apps
                )
                
                if not is_trusted:
                    # Fallback: check session allowlist
                    if not self._session.is_app_allowed(app_raw):
                        violations.append(
                            f"Step {step_num}: App '{app_raw}' not in trusted list. "
                            f"Allowed: {', '.join(sorted(self.trusted_apps))}"
                        )
                
                # Count retries
                total_retries += step.retries
                continue
            
            # Task 2: Validate open_url with domain allowlist
            if step.tool == "open_url":
                url = step.args.get("url", "")
                if not url:
                    violations.append(f"Step {step_num}: open_url missing url argument")
                    continue
                
                try:
                    from urllib.parse import urlparse
                    import re
                    
                    parsed = urlparse(url)
                    domain = parsed.netloc
                    
                    # Normalize domain (remove www. prefix)
                    if domain.startswith("www."):
                        domain = domain[4:]
                    
                    # Block IP addresses (security requirement)
                    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', domain):
                        violations.append(
                            f"Step {step_num}: IP addresses are not allowed for security (domain: {domain})"
                        )
                        continue
                    
                    # Check against trusted domains
                    if domain not in self.trusted_domains:
                        violations.append(
                            f"Step {step_num}: Domain '{domain}' not in trusted list. "
                            f"Allowed: {', '.join(sorted(self.trusted_domains))}"
                        )
                except Exception as e:
                    violations.append(f"Step {step_num}: Invalid URL format: {url}")
                
                total_retries += step.retries
                continue
            
            # Task: Validate restricted_shell with command allowlist
            if step.tool == "restricted_shell":
                engine = step.args.get("engine", "cmd")
                command = step.args.get("command", "")
                run_as_admin = step.args.get("run_as_admin", False)
                
                if not command:
                    violations.append(f"Step {step_num}: restricted_shell missing command argument")
                    continue
                
                # Validate using RestrictedShellTool
                try:
                    from assistant.tools.restricted_shell import RestrictedShellTool, SecurityError
                    
                    tool = RestrictedShellTool(self.restricted_shell_config)
                    
                    # Check if enabled
                    if not self.restricted_shell_config.get("enabled", False):
                        violations.append(
                            f"Step {step_num}: RestrictedShell is disabled. "
                            f"Enable in config/restricted_shell.json"
                        )
                        continue
                    
                    # Validate command against policy using public API
                    supervised = self._session.check() if self._session else False
                    tool.validate(engine, command, run_as_admin, supervised)
                    
                except SecurityError as e:
                    violations.append(f"Step {step_num}: {str(e)}")
                except Exception as e:
                    logger.error(f"[PlanGuard] RestrictedShell validation error: {e}")
                    violations.append(f"Step {step_num}: Shell validation failed: {str(e)}")
                
                total_retries += step.retries
                continue
            
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
            # Task 3: Safety audit logging
            try:
                import time
                audit_entry = {
                    "timestamp": time.time(),
                    "plan_id": plan.id,
                    "task": plan.task,
                    "violations": violations,
                    "step_count": len(plan.steps),
                    "tools_used": [step.tool for step in plan.steps]
                }
                
                # Create logs dir and append to audit log
                log_path = Path("logs/safety_audit.jsonl")
                log_path.parent.mkdir(exist_ok=True)
                
                with open(log_path, 'a') as f:
                    f.write(json.dumps(audit_entry) + "\n")
                
                logger.info(f"[PlanGuard] Logged {len(violations)} violations to safety_audit.jsonl")
            except Exception as e:
                logger.error(f"[PlanGuard] Failed to write audit log: {e}")
            
            raise PlanValidationError(
                f"Plan validation failed with {len(violations)} violation(s)",
                violations
            )

    def _check_dangerous_keypress(
        self, 
        step: "ActionStep", 
        step_num: int, 
        violations: list[str]
    ) -> None:
        """Check keypress for dangerous key combinations."""
        keys = step.args.get("keys", [])
        if isinstance(keys, str):
            keys = [keys]
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
    
    def _check_high_risk_step(
        self, 
        step: "ActionStep", 
        step_num: int, 
        violations: list[str]
    ) -> None:
        """Check high-risk step for dangerous patterns (legacy, mostly replaced by allowlists)."""
        if step.tool == "keypress":
            self._check_dangerous_keypress(step, step_num, violations)

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

