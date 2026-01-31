"""
Destructive Guardrails (W15.2).
Intercepts high-risk actions before they reach the executor.
"""

import re

from assistant.ui_contracts.schemas import ExecutionPlan


class DestructiveGuard:
    def __init__(self):
        # Regex patterns for dangerous commands
        self.dangerous_patterns = [
            r"(?i)rm\s+-[rf]+",  # rm -rf
            r"(?i)del\s+/s",  # del /s
            r"(?i)format\s+[a-z]:",  # format c:
            r"(?i)reg\s+delete",  # registry delete
            r"(?i)rd\s+/s",  # remove directory tree
        ]

    def validate(self, plan: ExecutionPlan) -> None:
        """
        Check plan for destructive actions.
        Raises ValueError if a violation is found.
        
        CRITICAL SECURITY FIX: Now checks ALL tools for dangerous patterns,
        not just run_command. This prevents bypasses via alternative tools.
        """
        for step in plan.steps:
            # Check ALL string arguments in ANY tool
            for arg_val in step.args.values():
                if not isinstance(arg_val, str):
                    continue

                val_lower = arg_val.lower()
                
                # Check regex patterns for dangerous commands
                for pattern in self.dangerous_patterns:
                    if re.search(pattern, val_lower):
                        raise ValueError(
                            f"⚠️ SAFETY BLOCK: Destructive command detected in tool '{step.tool}', step {step.id}: '{arg_val}'. Automatic execution denied."
                        )
                
                # Check wildcards with delete operations
                if ("*" in arg_val or "?" in arg_val):
                    if "del " in val_lower or "rm " in val_lower:
                        raise ValueError(
                            f"⚠️ SAFETY BLOCK: Wildcard deletion detected in tool '{step.tool}', step {step.id}: '{arg_val}'. Too risky for beta."
                        )

        # If clean
        return
