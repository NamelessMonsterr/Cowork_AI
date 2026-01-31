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
        """
        for step in plan.steps:
            # 1. Check Shell Commands
            if step.tool == "run_command":
                # Check all args for dangerous patterns (usually 'command' or 'cmd')
                # Safer to check all string values in args
                for arg_val in step.args.values():
                    if not isinstance(arg_val, str):
                        continue

                    val_lower = arg_val.lower()
                    for pattern in self.dangerous_patterns:
                        if re.search(pattern, val_lower):
                            raise ValueError(
                                f"⚠️ SAFETY BLOCK: Destructive command detected in step {step.id}: '{arg_val}'. Automatic execution denied."
                            )

            # 2. Check File Actions (Heuristic)

            # W15.2 Requirement: "delete/move > N files".
            # If we had structured file ops (e.g., delete_files), we'd check count here.
            # Currently 'computer' might expose specific file tools.
            # Wildcard deletes via command line are caught above.

            if step.tool == "run_command":
                for arg_val in step.args.values():
                    if not isinstance(arg_val, str):
                        continue

                    if "*" in arg_val or "?" in arg_val:
                        # Wildcards with delete commands
                        if "del " in arg_val.lower() or "rm " in arg_val.lower():
                            raise ValueError(
                                f"⚠️ SAFETY BLOCK: Wildcard deletion detected in step {step.id}: '{arg_val}'. Too risky for beta."
                            )

        # If clean
        return
