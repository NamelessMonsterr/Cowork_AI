"""
Restricted Shell Validator - Hardened command validation with unicode bypass prevention.

Security Features:
- Unicode normalization to prevent zero-width char bypasses
- Allowlist-based validation for CMD and PowerShell
- Dangerous pattern blocklist
- PowerShell flag blocking (- enc, -encodedcommand, -ExecutionPolicy Bypass, etc.)
- Output redaction for sensitive data
"""

import re
import unicodedata
import logging
from typing import List, Set

logger = logging.getLogger(__name__)


class RestrictedShellValidator:
    """
    Hardened validator for shell commands with unicode bypass prevention.
    
    Used by RestrictedShellTool to validate commands before execution.
    """
    
    # Dangerous PowerShell flags that enable bypass
    BLOCKED_PS_FLAGS = {
        "-enc", "-encodedcommand", "-e",  # Encoded command execution
        "-executionpolicy", "-ep", "-ex",  # Execution policy bypass
        "bypass", "unrestricted", "remotesigned",  # Policy levels
    }
    
    # Dangerous PowerShell cmdlets
    BLOCKED_PS_CMDLETS = {
        "invoke-expression", "iex",
        "invoke-webrequest", "iwr",
        "invoke-restmethod", "irm",
        "invoke-command", "icm",
        "start-bitstransfer",
        "downloadstring", "downloadfile",
    }
    
    # Dangerous command chaining/redirect patterns
    DANGEROUS_PATTERNS = [
        '|', '&', ';', '>', '<', '>>', '2>', '&&', '||',  # Standard
        '`', '^', '$(',  # Bash/PowerShell injection  '\n', '\r',  # Multiline
        '%COMSPEC%', '%SystemRoot%',  # Environment variable expansion
    ]
    
    def __init__(self, allowed_cmd: List[str], allowed_powershell: List[str]):
        """
        Initialize validator with allowlists.
        
        Args:
            allowed_cmd: List of allowed CMD commands
            allowed_powershell: List of allowed PowerShell cmdlets
        """
        self.allowed_cmd = {cmd.lower() for cmd in allowed_cmd}
        self.allowed_powershell = {cmd.lower() for cmd in allowed_powershell}
    
    def validate_command(self, engine: str, command: str) -> None:
        """
        Validate command with unicode normalization and hardened checks.
        
        Args:
            engine: "cmd" or "powershell"
            command: Command to validate
            
        Raises:
            SecurityError: If command violates policy
        """
        from assistant.tools.restricted_shell import SecurityError
        
        # Step 1: Unicode normalization (prevent zero-width char bypasses)
        normalized = self.normalize_unicode(command)
        
        # Step 2: Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in normalized:
                raise SecurityError(
                    f"Dangerous pattern not allowed: '{pattern}' in command"
                )
        
        # Step 3: Extract first token
        tokens = normalized.strip().split()
        if not tokens:
            raise SecurityError("Empty command")
        
        # Strip punctuation from first token (prevent bypasses like "dir." or "whoami!")
        first_token = tokens[0].strip('.,;:!?\'"-').lower()
        
        if not first_token:
            raise SecurityError("Invalid command token")
        
        # Step 4: Engine-specific validation
        if engine == "cmd":
            self._validate_cmd(first_token, normalized)
        elif engine == "powershell":
            self._validate_powershell(first_token, normalized)
        else:
            raise SecurityError(f"Invalid engine: {engine}")
    
    def _validate_cmd(self, first_token: str, command: str) -> None:
        """Validate CMD command."""
        from assistant.tools.restricted_shell import SecurityError
        
        if first_token not in self.allowed_cmd:
            allowed_display = ", ".join(list(self.allowed_cmd)[:10])
            if len(self.allowed_cmd) > 10:
                allowed_display += f" (+ {len(self.allowed_cmd) - 10} more)"
            raise SecurityError(
                f"Command '{first_token}' not in CMD allowlist. "
                f"Allowed: {allowed_display}"
            )
    
    def _validate_powershell(self, first_token: str, command: str) -> None:
        """Validate PowerShell command with flag blocking."""
        from assistant.tools.restricted_shell import SecurityError        
        # Check for blocked PowerShell flags
        command_lower = command.lower()
        for flag in self.BLOCKED_PS_FLAGS:
            if flag in command_lower:
                raise SecurityError(
                    f"Blocked PowerShell flag detected: '{flag}'"
                )
        
        # Check for blocked cmdlets
        for cmdlet in self.BLOCKED_PS_CMDLETS:
            if cmdlet in command_lower:
                raise SecurityError(
                    f"Blocked PowerShell cmdlet detected: '{cmdlet}'"
                )
        
        # Check allowlist
        if first_token not in self.allowed_powershell:
            allowed_display = ", ".join(list(self.allowed_powershell)[:10])
            if len(self.allowed_powershell) > 10:
                allowed_display += f" (+ {len(self.allowed_powershell) - 10} more)"
            raise SecurityError(
                f"Cmdlet '{first_token}' not in PowerShell allowlist. "
                f"Allowed: {allowed_display}"
            )
    
    @staticmethod
    def normalize_unicode(text: str) -> str:
        """
        Normalize unicode to prevent zero-width character bypasses.
        
        Args:
            text: Input text
            
        Returns:
            Normalized text with zero-width chars removed
        """
        # NFKC normalization (compatibility decomposition + canonical composition)
        normalized = unicodedata.normalize('NFKC', text)
        
        # Remove zero-width characters
        zero_width_chars = [
            '\u200b',  # Zero-width space
            '\u200c',  # Zero-width non-joiner
            '\u200d',  # Zero-width joiner
            '\ufeff',  # Zero-width no-break space
        ]
        for char in zero_width_chars:
            normalized = normalized.replace(char, '')
        
        return normalized
