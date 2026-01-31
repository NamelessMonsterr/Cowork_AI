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
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

from assistant.safety.destructive_guard import DestructiveGuard
from assistant.safety.user_profile_manager import UserProfileManager
from assistant.ui_contracts.schemas import ActionStep, ExecutionPlan

from .session_auth import SessionAuth

logger = logging.getLogger(__name__)


# P3 FIX: Setup rotating file handler for safety audit
# Prevents disk full scenarios (10MB per file, 5 backups = 50MB total)
def _setup_audit_logger():
    """Setup rotating file handler for safety audit logs."""
    audit_logger = logging.getLogger("safety_audit")
    audit_logger.setLevel(logging.INFO)

    # Only add handler if not already configured
    if not audit_logger.handlers:
        log_path = Path("logs/safety_audit.jsonl")
        log_path.parent.mkdir(exist_ok=True)

        handler = RotatingFileHandler(
            str(log_path),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        formatter = logging.Formatter("%(message)s")  # JSON lines don't need extra formatting
        handler.setFormatter(formatter)
        audit_logger.addHandler(handler)

    return audit_logger


# Initialize audit logger
_audit_logger = _setup_audit_logger()


class PlanValidationError(Exception):
    """Raised when plan validation fails."""

    def __init__(self, message: str, violations: list[str]):
        super().__init__(message)
        self.violations = violations


@dataclass
class PlanGuardConfig:
    """Configuration for plan validation."""

    max_steps: int = 50  # P4 FIX: Hard limit to prevent DoS via large plans
    max_high_risk_steps: int = 0  # By default, block all high-risk
    max_retries_total: int = 20
    require_verification: bool = True  # Each step must have verify OR marked unverifiable
    allowed_tools: set[str] | None = None  # None = allow all known tools
    blocked_domains: set[str] = None
    trusted_domains: set[str] = None  # P0-1: Allowlist for open_url

    def __post_init__(self):
        if self.blocked_domains is None:
            self.blocked_domains = {
                "*.exe",  # Direct executables
                "registry",  # Registry modifications
                "admin",  # Admin operations
            }

        # Default trusted domains if None
        if self.trusted_domains is None:
            self.trusted_domains = {
                "google.com",
                "wikipedia.org",
                "github.com",
                "stackoverflow.com",
                "python.org",
                "microsoft.com",
            }


# HARDENED SECURITY POLICY

# Task 3: Removed 'drag' from SAFE_TOOLS (destructive risk)
# Safe tools - always allowed, no additional validation
SAFE_TOOLS = {
    # Mouse actions (drag REMOVED - can delete files, leak data)
    "click",
    "double_click",
    "right_click",
    "scroll",
    "move",
    # Keyboard actions (keypress validated for dangerous combos)
    "type",
    "type_text",
    "keypress",
    # Window actions
    "focus_window",
    "get_active_window",
    # Utility
    "wait",
    "screenshot",
    # Voice feedback - safe, non-destructive output
    "speak",
}

# Restricted but safe tools - require allowlist validation
RESTRICTED_SAFE_TOOLS = {
    "open_app",  # Safe if app in TRUSTED_APPS
    "open_url",  # Safe if domain in TRUSTED_DOMAINS
    "restricted_shell",  # Safe if command in ALLOWED_COMMANDS
}

# Task 5: Expanded blocklist - indirect attack vectors
BLOCKED_TOOLS = {
    # Shell/command execution
    "run_shell",
    "shell",
    "cmd",
    "powershell",
    "bash",
    "run_command",
    "exec",
    "eval",
    # File system operations (indirect attack vectors)
    "delete_file",
    "write_file",
    "read_file",
    "list_dir",
    "upload_file",
    "download",
    # Clipboard (data leakage risk)
    "clipboard_get",
    "clipboard_set",
    # System modification
    "registry_edit",
    "set_env",
    "install",
    # File operations that were in RESTRICTED (now blocked)
    "open_file",
    "save_file",
}

# Task 1: Fallback trusted apps (config-driven preferred)
TRUSTED_APPS_DEFAULT = {
    "notepad",
    "notepad.exe",
    "calc",
    "calc.exe",
    "calculator",
    "calculator.exe",
    "mspaint",
    "mspaint.exe",
    "paint",
    "wordpad",
    "wordpad.exe",
}

# Task 4: All known tools for default-deny validation
ALL_KNOWN_TOOLS = SAFE_TOOLS | RESTRICTED_SAFE_TOOLS | BLOCKED_TOOLS

# Legacy high-risk tools list (mostly replaced by allowlists)
HIGH_RISK_TOOLS = {
    "keypress",  # Validated for dangerous key combinations
}


# Task 1: Load trusted apps from config
def load_trusted_apps() -> tuple[set, dict]:
    """Load trusted apps configuration from JSON.
    
    P0 CRITICAL: Validates that wildcard ("*") is NOT present in trusted_apps.
    If wildcard detected, system refuses to start (fail-fast security).
    
    Returns:
        tuple: (trusted_apps_set, app_aliases_dict)
    
    Raises:
        SystemExit: If wildcard detected in configuration (CRITICAL security violation)
    """
    config_path = Path("assistant/config/trusted_apps.json")
    if not config_path.exists():
        logger.warning(f"Trusted apps config not found at {config_path}, using defaults")
        return (
            {
                "notepad",
                "calc",
                "mspaint",
                "chrome",
                "msedge",
                "firefox",
                "code",
                "explorer",
            },
            {"calculator": "calc", "vscode": "code", "edge": "msedge"},
        )

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    trusted_apps = set(data.get("trusted_apps", []))
    app_aliases = data.get("app_aliases", {})

    # P0 CRITICAL SECURITY CHECK: Prevent wildcard bypass
    if "*" in trusted_apps:
        logger.critical("=" * 80)
        logger.critical("🔴 CRITICAL SECURITY VIOLATION DETECTED")
        logger.critical("=" * 80)
        logger.critical("Wildcard ('*') detected in trusted_apps.json")
        logger.critical("This configuration allows ANY application to execute,")
        logger.critical("completely bypassing PlanGuard security controls.")
        logger.critical("")
        logger.critical("REFUSING TO START - Fix required:")
        logger.critical(f"Edit {config_path} and replace wildcard with explicit app list")
        logger.critical("=" * 80)
        import sys

        sys.exit(1)  # Fail-fast - do not allow system to start

    # Additional validation: ensure no empty string tricks
    if "" in trusted_apps or " " in trusted_apps:
        logger.critical("Invalid empty/whitespace entry in trusted_apps - refusing to start")
        import sys

        sys.exit(1)

    logger.info(f"Loaded {len(trusted_apps)} trusted apps and {len(app_aliases)} aliases")
    logger.info(f"Trusted apps: {', '.join(sorted(trusted_apps))}")

    return trusted_apps, app_aliases


def load_trusted_domains() -> set:
    """
    Load trusted domains from config with fallback to defaults.
    Returns: set of trusted domain strings
    """
    try:
        config_path = Path(__file__).parent.parent / "config" / "trusted_domains.json"
        if config_path.exists():
            with open(config_path) as f:
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
            with open(config_path) as f:
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
        config: PlanGuardConfig | None = None,
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
       
        # P1.5: User-specific profile manager
        try:
            self.profile_manager = UserProfileManager()
            logger.info("[PlanGuard] UserProfileManager enabled")
        except Exception as e:
            logger.warning(f"[PlanGuard] UserProfileManager initialization failed: {e}")
            self.profile_manager = None

        # Task 1: Load config-driven trusted apps and domains
        self.trusted_apps, self.app_aliases = load_trusted_apps()

        # Prefer config trusted_domains if set (for testing/overrides)
        if self._config.trusted_domains:
            self.trusted_domains = self._config.trusted_domains
        else:
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
            violations.append(f"Plan has {len(plan.steps)} steps, max allowed is {self._config.max_steps}")

        # 2. Count risk levels and check tools
        high_risk_count = 0
        total_retries = 0

        for i, step in enumerate(plan.steps):
            step_num = i + 1

            # Task 4: Default-deny - Check if tool is recognized
            if step.tool not in ALL_KNOWN_TOOLS:
                # Special case: plugin tools
                if step.tool.startswith("plugin:"):
                    violations.append(f"Step {step_num}: Plugin tools require explicit permission")
                else:
                    violations.append(
                        f"Step {step_num}: Tool '{step.tool}' is not recognized. "
                        f"Allowed tools: {', '.join(sorted(SAFE_TOOLS | RESTRICTED_SAFE_TOOLS))}"
                    )
                continue

            # Block dangerous tools
            if step.tool in BLOCKED_TOOLS:
                violations.append(f"Step {step_num}: Tool '{step.tool}' is blocked for safety")
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

                # P1.5: Check user-specific profile first
                user_id = getattr(self._session, 'user_id', None)
                is_allowed_by_profile = False
                
                if user_id and self.profile_manager:
                    # Check user's profile permissions
                    is_allowed_by_profile = self.profile_manager.validate_app(user_id, exe_no_ext)
                    
                    if is_allowed_by_profile:
                        logger.info(
                            f"[PlanGuard] ✅ App '{app_raw}' allowed for user '{user_id}' "
                            f"via profile permissions"
                        )
                        total_retries += step.retries
                        continue
                
                # Fallback: Check global trusted list (for backward compatibility)
                is_trusted = (
                    exe_name in self.trusted_apps
                    or exe_no_ext in self.trusted_apps
                    or resolved_name in self.trusted_apps
                )

                if not is_trusted and not is_allowed_by_profile:
                    # Final fallback: check session allowlist
                    if not self._session.is_app_allowed(app_raw):
                        if user_id:
                            violations.append(
                                f"Step {step_num}: App '{app_raw}' not allowed for user '{user_id}' profile. "
                                f"Global allowed: {', '.join(sorted(self.trusted_apps))}"
                            )
                        else:
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
                    import ipaddress
                    from urllib.parse import urlparse

                    parsed = urlparse(url)
                    domain = parsed.netloc

                    # Normalize domain (remove www. prefix)
                    if domain.startswith("www."):
                        domain = domain[4:]

                    # SECURITY FIX: Block IP addresses (IPv4, IPv6, localhost, private networks)
                    # Remove port if present
                    host = domain.split(":")[0]

                    # Check for localhost variants
                    if host.lower() in [
                        "localhost",
                        "127.0.0.1",
                        "::1",
                        "0.0.0.0",
                        "::",
                    ]:
                        violations.append(f"Step {step_num}: Localhost addresses are not allowed for security")
                        logger.warning(f"[PlanGuard] Blocked localhost URL: {url}")
                        continue

                    # Check if it's an IP address (IPv4 or IPv6)
                    is_ip = False
                    try:
                        ip_obj = ipaddress.ip_address(host)
                        is_ip = True

                        # Check if it's a private network
                        if ip_obj.is_private:
                            violations.append(
                                f"Step {step_num}: Private IP addresses are not allowed for security (IP: {host})"
                            )
                            logger.warning(f"[PlanGuard] Blocked private IP URL: {url}")
                            continue

                        # Block all IPs for SSRF prevention
                        violations.append(f"Step {step_num}: IP addresses are not allowed for security (IP: {host})")
                        logger.warning(f"[PlanGuard] Blocked IP URL: {url}")
                        continue
                    except ValueError:
                        # Not an IP address, continue with domain validation
                        pass

                    # Domain allowlist check with subdomain support
                    domain_lower = domain.lower()
                    allowed = False
                    for trusted in self.trusted_domains:
                        trusted_lower = trusted.lower()
                        # Exact match OR subdomain match
                        if domain_lower == trusted_lower or domain_lower.endswith("." + trusted_lower):
                            allowed = True
                            break

                    if not allowed:
                        violations.append(
                            f"Step {step_num}: Domain '{domain}' not in trusted list. "
                            f"Allowed: {', '.join(sorted(self.trusted_domains))}"
                        )
                except Exception:
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
                    from assistant.tools.restricted_shell import (
                        RestrictedShellTool,
                        SecurityError,
                    )

                    tool = RestrictedShellTool(self.restricted_shell_config)

                    # Check if enabled
                    if not self.restricted_shell_config.get("enabled", False):
                        violations.append(
                            f"Step {step_num}: RestrictedShell is disabled. Enable in config/restricted_shell.json"
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
                    violations.append(f"Step {step_num}: Path '{path}' is not in allowed folders")

            # Increment high risk count
            if step.risk_level == "high":
                high_risk_count += 1

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

                # Sanitize strings to prevent log injection
                audit_entry = {
                    "timestamp": time.time(),
                    "plan_id": plan.id,
                    "task": plan.task.replace("\n", "\\n").replace("\r", ""),
                    "violations": [v.replace("\n", "\\n").replace("\r", "") for v in violations],
                    "step_count": len(plan.steps),
                    "tools_used": [step.tool for step in plan.steps],
                }

                # P3 FIX: Use rotating file handler instead of direct write
                _audit_logger.info(json.dumps(audit_entry))

                logger.info(f"[PlanGuard] Logged {len(violations)} violations to safety_audit.jsonl")
            except Exception as e:
                logger.error(f"[PlanGuard] Failed to write audit log: {e}")

            raise PlanValidationError(
                f"Plan validation failed with {len(violations)} violation(s)",
                violations,
            )

    def _check_dangerous_keypress(self, step: "ActionStep", step_num: int, violations: list[str]) -> None:
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
                violations.append(f"Step {step_num}: Blocked dangerous keypress {name}")

    def _check_high_risk_step(self, step: "ActionStep", step_num: int, violations: list[str]) -> None:
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
