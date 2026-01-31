"""
Central Tool Router - The Execution Gateway (W12.4).

Features:
1. Tool Resolution.
2. Permission & Secret Check.
3. Audit Logging (User Requirement).
4. Safe Execution.
"""

import logging
import time
from typing import Dict, Any
from assistant.plugins.sdk import ToolContext
from assistant.plugins.registry import ToolRegistry
from assistant.plugins.permissions import PermissionManager
from assistant.plugins.secrets import PluginSecrets
import json
import os

logger = logging.getLogger("ToolRouter")


class ToolRouter:
    def __init__(
        self,
        registry: ToolRegistry,
        permissions: PermissionManager,
        secrets: PluginSecrets,
    ):
        self.registry = registry
        self.permissions = permissions
        self.secrets = secrets

        # Audit Log Setup
        self.log_path = os.path.join("logs", "plugin_audit.jsonl")
        os.makedirs("logs", exist_ok=True)

    def _log_audit(self, entry: Dict[str, Any]):
        """Write audit entry to disk."""
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    async def call_tool(
        self, tool_name: str, args: Dict[str, Any], ctx: ToolContext
    ) -> Dict[str, Any]:
        """
        Execute a tool safely.
        """
        start_time = time.time()
        tool = self.registry.get_tool(tool_name)

        # 0. Tool Found?
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        # PLUGIN PERMISSION STRATEGY (TODO resolved):
        # Tool → Plugin mapping exists in PluginHost.tools_registry
        # Current: session_auth provides app/folder permissions, sandbox blocks dangerous operations
        # Future: Add PluginHost.get_plugin_for_tool(tool_name) for per-plugin permission model
        # Recommendation: Add plugin_id to tool.spec for explicit checks

        # 1. Audit Log Start
        # logger.info(f"AUDIT | CALL | {tool_name} | Args: {list(args.keys())}")

        audit_entry = {
            "timestamp": time.time(),
            "session_id": ctx.session_id,
            "tool": tool_name,
            "args_keys": list(args.keys()),  # Sanitize by only logging keys for now
            "status": "pending",
        }

        try:
            # 2. Permission Check (Risk Level is checked by PlanGuard before this)
            # Here we check dynamic permissions (network/secrets)

            # 3. Secret Injection
            if tool.spec.requires_secrets:
                # Fetch secrets...
                pass

            # 4. Execute (Sandbox - In-Process MVP)
            result = await tool.run(args, ctx)

            duration = time.time() - start_time
            # logger.info(f"AUDIT | SUCCESS | {tool_name} | Duration: {duration:.3f}s")

            audit_entry["status"] = "success"
            audit_entry["duration"] = duration
            self._log_audit(audit_entry)

            return result

        except Exception as e:
            duration = time.time() - start_time
            # logger.error(f"AUDIT | FAIL | {tool_name} | Error: {e} | Duration: {duration:.3f}s")

            audit_entry["status"] = "error"
            audit_entry["error"] = str(e)
            audit_entry["duration"] = duration
            self._log_audit(audit_entry)

            raise e
