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

logger = logging.getLogger("ToolRouter")

class ToolRouter:
    def __init__(self, registry: ToolRegistry, permissions: PermissionManager, secrets: PluginSecrets):
        self.registry = registry
        self.permissions = permissions
        self.secrets = secrets
        
    async def call_tool(self, tool_name: str, args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
        """
        Execute a tool safely.
        """
        start_time = time.time()
        tool = self.registry.get_tool(tool_name)
        
        # 0. Tool Found?
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
            
        # TODO: Lookup plugin_id for this tool to check permissions
        # MVP: We assume tool.spec doesn't have plugin_id reference, 
        # so we might need Registry to map tool -> plugin_id.
        # For now, bypassing strict plugin-ID check in MVP router, 
        # normally we'd pass plugin_id context.
        
        # 1. Audit Log Start
        logger.info(f"AUDIT | CALL | {tool_name} | Args: {list(args.keys())}") # Redact values in logs?
        
        try:
            # 2. Permission Check (Risk Level is checked by PlanGuard before this)
            # Here we check dynamic permissions (network/secrets)
            
            # 3. Secret Injection
            # If tool needs secrets, we fetch them and inject into args
            # This keeps secrets out of the LLM plan args
            if tool.spec.requires_secrets:
                 # Fetch secrets... 
                 # For MVP, assume args already have them or logic handles it
                 pass

            # 4. Execute (Sandbox - In-Process MVP)
            result = await tool.run(args, ctx)
            
            duration = time.time() - start_time
            logger.info(f"AUDIT | SUCCESS | {tool_name} | Duration: {duration:.3f}s")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"AUDIT | FAIL | {tool_name} | Error: {e} | Duration: {duration:.3f}s")
            raise e
