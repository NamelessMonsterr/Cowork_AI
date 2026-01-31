"""
RestrictedShellTool - Safe command-line execution with strict controls.

Security Features:
- Allowlist-based command validation
- Pattern blocking for dangerous operations
- Output redaction for sensitive data
- Audit logging for all executions
- Admin escalation controls
- Timeout protection

Usage:
    tool = RestrictedShellTool()
    result = tool.execute(
        engine="cmd",
        command="ipconfig /all",
        run_as_admin=False
    )
    print(result.stdout)
"""

import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when command violates security policy."""

    pass


@dataclass
class ShellResult:
    """Result from shell command execution."""

    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: int
    redacted: bool = False
    command: str = ""
    engine: str = ""


class RestrictedShellTool:
    """
    Executes shell commands with strict security controls.

    Security Model:
    - Default-deny: Only allowlisted commands execute
    - Pattern blocking: Blocks dangerous patterns (rm, del, format, etc.)
    - No chaining: Blocks pipes, redirects, command chains
    - Output redaction: Removes API keys, passwords from output
    - Audit logging: Logs all executions to JSONL
    - P1 SECURITY: Folder sandboxing, file size limits, content redaction
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize tool with configuration.

        Args:
            config: Config dict (not path). If None, loads from file.
        """
        if config is None:
            config = self._load_config()
        self.config = config
        self._load_folder_config()

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from restricted_shell.json."""
        try:
            config_path = Path(__file__).parent.parent / "config" / "restricted_shell.json"
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                    logger.info(
                        f"[RestrictedShell] Loaded config with {len(config.get('allowed_cmd', []))} cmd commands"
                    )
                    return config
        except Exception as e:
            logger.warning(f"[RestrictedShell] Failed to load config: {e}")

        # Default: disabled
        return {"enabled": False}

    def _load_folder_config(self):
        """Load P1 folder sandboxing configuration."""
        try:
            folder_config_path = Path(__file__).parent.parent / "config" / "trusted_folders.json"
            if folder_config_path.exists():
                with open(folder_config_path) as f:
                    folder_config = json.load(f)
                    
                    # Expand environment variables in allowed_roots
                    self.allowed_roots = [
                        Path(os.path.expandvars(root)) 
                        for root in folder_config.get("allowed_roots", [])
                    ]
                    self.blocked_paths = folder_config.get("blocked_paths", [])
                    self.max_file_size_mb = folder_config.get("max_file_size_mb", 10)
                    self.blocked_extensions = folder_config.get("blocked_extensions", [])
                    
                    logger.info(
                        f"[RestrictedShell] P1 Sandbox: {len(self.allowed_roots)} allowed roots, "
                        f"{len(self.blocked_paths)} blocked patterns"
                    )
        except Exception as e:
            logger.warning(f"[RestrictedShell] Failed to load folder config: {e}")
            # Fallback to safe defaults
            self.allowed_roots = [
                Path.home() / "Documents",
                Path.home() / "Desktop",
            ]
            self.blocked_paths = ["*\\Windows\\*", "*\\.ssh\\*"]
            self.max_file_size_mb = 10
            self.blocked_extensions = [".exe", ".key", ".pem"]

    def validate_path(self, path: str) -> Path:
        """
        P1 SECURITY: Validate file path against sandbox rules.
        
        Args:
            path: File or directory path to validate
        
        Returns:
            Resolved Path object if valid
        
        Raises:
            SecurityError: If path violates sandbox rules
        """
        try:
            real_path = Path(path).resolve()
        except Exception as e:
            raise SecurityError(f"Invalid path: {e}")
        
        # Check blocked patterns
        path_str = str(real_path).replace("/", "\\")
        for pattern in self.blocked_paths:
            # Convert glob pattern to regex
            regex_pattern = pattern.replace("*", ".*").replace("\\", "\\\\")
            if re.match(regex_pattern, path_str, re.IGNORECASE):
                logger.critical(f"🔴 P1 BLOCKED: Path matches blocked pattern '{pattern}': {path}")
                raise SecurityError(f"Access denied: {path} matches blocked pattern")
        
        # Check allowed roots (sandbox)
        if self.allowed_roots:
            is_allowed = False
            for allowed_root in self.allowed_roots:
                try:
                    real_path.relative_to(allowed_root)
                    is_allowed = True
                    break
                except ValueError:
                    continue
            
            if not is_allowed:
                logger.critical(f"🔴 P1 BLOCKED: Path outside sandbox: {path}")
                logger.critical(f"Allowed roots: {[str(r) for r in self.allowed_roots]}")
                raise SecurityError(
                    f"Access denied: {path} is outside allowed directories. "
                    f"Only {', '.join([r.name for r in self.allowed_roots])} folders are accessible."
                )
        
        # Check file extension
        if real_path.suffix.lower() in self.blocked_extensions:
            logger.critical(f"🔴 P1 BLOCKED: Blocked file extension: {real_path.suffix}")
            raise SecurityError(f"Access denied: {real_path.suffix} files are blocked")
        
        # Check file size (if file exists)
        if real_path.exists() and real_path.is_file():
            size_mb = real_path.stat().st_size / (1024 * 1024)
            if size_mb > self.max_file_size_mb:
                logger.critical(f"🔴 P1 BLOCKED: File too large: {size_mb:.1f}MB (max {self.max_file_size_mb}MB)")
                raise SecurityError(
                    f"File too large: {size_mb:.1f}MB exceeds limit of {self.max_file_size_mb}MB"
                )
        
        logger.debug(f"✅ P1 Path validated: {path}")
        return real_path

    def validate(
        self,
        engine: str,
        command: str,
        run_as_admin: bool = False,
        supervised: bool = False,
    ) -> None:
        """
        Public validation method for PlanGuard integration.

        Args:
            engine: "cmd" or "powershell"
            command: Command to validate
            run_as_admin: Whether admin elevation is requested
            supervised: Whether execution is supervised

        Raises:
            SecurityError: If command violates policy
        """
        self._validate_command(engine, command, run_as_admin, supervised)

    def execute(
        self,
        engine: str,
        command: str,
        run_as_admin: bool = False,
        supervised: bool = False,
    ) -> ShellResult:
        """
        Execute command with strict safety controls.

        Args:
            engine: "cmd" or "powershell"
            command: Command to execute
            run_as_admin: Whether to request admin elevation
            supervised: Whether execution is supervised by user

        Returns:
            ShellResult with output and metadata

        Raises:
            SecurityError: If command violates policy
        """
        # Validate against policy
        self._validate_command(engine, command, run_as_admin, supervised)

        # Execute with timeout
        start_time = time.time()
        try:
            result = self._execute_safe(engine, command, run_as_admin)
        except subprocess.TimeoutExpired:
            logger.error(f"[RestrictedShell] Command timeout: {command}")
            raise SecurityError(f"Command exceeded timeout of {self.config.get('timeout_seconds', 30)}s")

        execution_time = int((time.time() - start_time) * 1000)

        # Redact sensitive data
        stdout_redacted = self._redact_sensitive(result.stdout)
        stderr_redacted = self._redact_sensitive(result.stderr)
        redacted = (stdout_redacted != result.stdout) or (stderr_redacted != result.stderr)

        # Audit log
        self._audit_log(engine, command, result.returncode, execution_time, run_as_admin)

        logger.info(f"[RestrictedShell] Executed {engine}: {command[:50]}... exit={result.returncode}")

        return ShellResult(
            stdout=stdout_redacted,
            stderr=stderr_redacted,
            exit_code=result.returncode,
            execution_time_ms=execution_time,
            redacted=redacted,
            command=command,
            engine=engine,
        )

    def _validate_command(self, engine: str, command: str, run_as_admin: bool, supervised: bool):
        """
        Validate command against security policy.

        Raises:
            SecurityError: If validation fails
        """
        # Check if enabled
        if not self.config.get("enabled", False):
            raise SecurityError("RestrictedShell is disabled in configuration")

        # Check admin escalation
        if run_as_admin:
            if not self.config.get("allow_admin", False):
                raise SecurityError("Admin execution is disabled in configuration")
            if not supervised:
                raise SecurityError("Admin execution requires supervised mode")

        # Check engine validity
        if engine not in ["cmd", "powershell"]:
            raise SecurityError(f"Invalid engine: {engine}. Must be 'cmd' or 'powershell'")

        # SECURITY FIX: Use hardened validator with unicode normalization
        from assistant.safety.shell_validator import RestrictedShellValidator

        validator = RestrictedShellValidator(
            allowed_cmd=self.config.get("allowed_cmd", []),
            allowed_powershell=self.config.get("allowed_powershell", []),
        )

        # Validate with enhanced checks (unicode normalization, PowerShell flags, etc.)
        validator.validate_command(engine, command)

        # Check blocked patterns (in addition to validator checks)
        command_lower = command.lower()
        for pattern in self.config.get("blocked_patterns", []):
            if pattern.lower() in command_lower:
                raise SecurityError(f"Blocked pattern detected: '{pattern}'")

    def _execute_safe(self, engine: str, command: str, run_as_admin: bool) -> subprocess.CompletedProcess:
        """
        Execute command safely with subprocess.

        SECURITY: Admin escalation never auto-clicks UAC.
        Admin execution requires supervised mode + manual approval.
        If UAC appears, system enters takeover mode.

        Returns:
            CompletedProcess with stdout/stderr/returncode
        """
        # HARDENED: Enforce timeout from config
        timeout = self.config.get("timeout_seconds", 30)

        if engine == "cmd":
            # Execute via cmd.exe
            full_command = ["cmd.exe", "/c", command]
        else:  # powershell
            # Execute via PowerShell with restricted execution policy
            full_command = [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Restricted",
                "-Command",
                command,
            ]

        # SECURITY: Admin escalation
        # NEVER attempt to automate UAC clicks (critical security violation)
        # If UAC appears, system must pause and enter takeover mode
        if run_as_admin:
            logger.warning("[RestrictedShell] Admin execution requested - requires supervised mode")
            logger.warning("[RestrictedShell] UAC automation is NEVER attempted (security policy)")
            # SECURITY POLICY: Admin elevation with supervised confirmation
            # 1. User must explicitly grant 'supervised' mode
            # 2. Command must pass RestrictedShellValidator checks
            # 3. If UAC secure desktop appears → Trigger takeover mode (user clicks manually)
            # 4. System NEVER attempts pywinauto/SendKeys on UAC dialog
            # Implementation: Current behavior is correct - no automation needed
            # This enforces principle of least privilege and prevents privilege escalation attacks

        # Execute with ENFORCED timeout
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=timeout,  # HARDENED: Timeout enforced
            shell=False,  # Security: Never use shell=True
        )

        return result

    def _redact_sensitive(self, text: str) -> str:
        """
        Redact sensitive data from output.

        Args:
            text: Output text

        Returns:
            Text with sensitive data replaced with [REDACTED]
        """
        if not text:
            return text

        redacted = text
        for pattern in self.config.get("redaction_patterns", []):
            try:
                redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)
            except re.error:
                logger.warning(f"[RestrictedShell] Invalid redaction pattern: {pattern}")

        return redacted

    def _audit_log(
        self,
        engine: str,
        command: str,
        exit_code: int,
        execution_time_ms: int,
        run_as_admin: bool,
    ):
        """
        Log execution to audit file.

        Args:
            engine: cmd or powershell
            command: Executed command
            exit_code: Process exit code
            execution_time_ms: Execution time in milliseconds
            run_as_admin: Whether admin was requested
        """
        try:
            log_path = Path("logs/restricted_shell_audit.jsonl")
            log_path.parent.mkdir(exist_ok=True)

            entry = {
                "timestamp": time.time(),
                "engine": engine,
                "command": command,
                "run_as_admin": run_as_admin,
                "exit_code": exit_code,
                "execution_time_ms": execution_time_ms,
            }

            with open(log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")

        except Exception as e:
            logger.error(f"[RestrictedShell] Failed to write audit log: {e}")
