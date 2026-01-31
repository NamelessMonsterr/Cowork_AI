"""
Destructive Guardrails (W15.2).
Intercepts high-risk actions before they reach the executor.
"""

import re
import shlex

from assistant.ui_contracts.schemas import ExecutionPlan


class DestructiveGuard:
    def __init__(self):
        # Regex patterns for dangerous commands
        # HIGH SECURITY FIX: Enhanced patterns to prevent obfuscation bypasses
        self.dangerous_patterns = [
            # rm variations (spaces, tabs, quotes, variables)
            r"(?i)\brm\s+.*-[rf]+",
            r"(?i)\brm\s+.*['\"]?-[rf]['\"]?",
            # del variations
            r"(?i)\bdel\s+.*/[sq]",
            r"(?i)\bdel\s+.*['\"]?/[sq]['\"]?",
            # format drive
            r"(?i)\bformat\s+[a-z]:",
            r"(?i)\bformat\s+['\"]?[a-z]:['\"]?",
            # registry delete
            r"(?i)\breg\s+delete",
            r"(?i)\breg\s+['\"]?delete['\"]?",
            # remove directory tree
            r"(?i)\brd\s+.*/s",
            r"(?i)\brd\s+.*['\"]?/s['\"]?",
            # PowerShell dangerous cmdlets
            r"(?i)remove-item\s+.*-recurse",
            r"(?i)remove-item\s+.*-force",
        ]
        
        # HIGH SECURITY FIX: Dangerous keywords that shouldn't appear in commands
        self.dangerous_keywords = {
            "format", "fdisk", "mkfs", "dd if=/dev/zero",
            ":(){ :|:& };:",  # Fork bomb
            "rm -rf /", "del /s",
        }

    def _normalize_command(self, cmd: str) -> str:
        """
        Normalize command to detect obfuscation.
        
        HIGH SECURITY FIX: Handles quotes, escapes, variables
        """
        # Remove common obfuscation techniques
        normalized = cmd.replace("'", "").replace('"', "")
        normalized = normalized.replace("\\", "")
        normalized = normalized.replace("$", "")
        normalized = normalized.replace("`", "")
        
        # Collapse whitespace
        normalized = " ".join(normalized.split())
        
        return normalized.lower()

    def validate(self, plan: ExecutionPlan) -> None:
        """
        Check plan for destructive actions.
        Raises ValueError if a violation is found.
        
        CRITICAL SECURITY FIX: Now checks ALL tools for dangerous patterns
        HIGH SECURITY FIX: Enhanced to prevent regex obfuscation bypasses
        """
        for step in plan.steps:
            # Check ALL string arguments in ANY tool
            for arg_val in step.args.values():
                if not isinstance(arg_val, str):
                    continue

                val_lower = arg_val.lower()
                normalized = self._normalize_command(arg_val)
                
                # Check for dangerous keywords (post-normalization)
                for keyword in self.dangerous_keywords:
                    if keyword in normalized:
                        raise ValueError(
                            f"⚠️ SAFETY BLOCK: Dangerous keyword '{keyword}' detected in tool '{step.tool}', step {step.id}. Automatic execution denied."
                        )
                
                # Check regex patterns (original and normalized)
                for pattern in self.dangerous_patterns:
                    if re.search(pattern, val_lower) or re.search(pattern, normalized):
                        raise ValueError(
                            f"⚠️ SAFETY BLOCK: Destructive command detected in tool '{step.tool}', step {step.id}: '{arg_val}'. Automatic execution denied."
                        )
                
                # Check wildcards with delete operations
                if ("*" in arg_val or "?" in arg_val):
                    if "del " in val_lower or "rm " in val_lower or "remove" in val_lower:
                        raise ValueError(
                            f"⚠️ SAFETY BLOCK: Wildcard deletion detected in tool '{step.tool}', step {step.id}: '{arg_val}'. Too risky for beta."
                        )

        # If clean
        return
