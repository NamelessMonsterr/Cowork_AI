"""
W12 Verification - Plugin System Demo.
"""

import os
import sys

sys.path.append(os.getcwd())
import asyncio
import logging

from assistant.plugins.permissions import PermissionManager
from assistant.plugins.registry import PluginLoader, ToolRegistry
from assistant.plugins.router import ToolRouter
from assistant.plugins.sdk import ToolContext
from assistant.plugins.secrets import PluginSecrets

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("W12_Demo")


async def main():
    logger.info("--- W12 Plugin System Verification ---")

    # 1. Initialize Stack
    registry = ToolRegistry()
    loader = PluginLoader(registry)

    # Mock builtins path for this test
    loader.search_paths = [os.path.join(os.getcwd(), "assistant", "plugins", "builtins")]

    # 2. Load Plugins
    logger.info("Loading plugins...")
    loader.load_all()

    tools = registry.list_tools()
    logger.info(f"Loaded Tools: {[t.spec.name for t in tools]}")

    if "read_clipboard" not in [t.spec.name for t in tools]:
        logger.error("❌ Clipboard plugin not loaded!")
        return

    # 3. Setup Router & Permissions
    permissions = PermissionManager()
    secrets = PluginSecrets()
    router = ToolRouter(registry, permissions, secrets)

    # Grant permissions
    # In real app, UI would do this.
    permissions.grant("cowork.clipboard", ["clipboard"])

    # 4. Execute Tool
    ctx = ToolContext(session_id="test_session")

    # Test Write
    logger.info("Executing write_clipboard...")
    await router.call_tool("write_clipboard", {"text": "W12 Success!"}, ctx)

    # Test Read
    logger.info("Executing read_clipboard...")
    result = await router.call_tool("read_clipboard", {}, ctx)
    logger.info(f"Read Result: {result}")

    if result.get("content") == "W12 Success!":
        logger.info("✅ Verification Passed!")
    else:
        logger.error("❌ Content mismatch.")


if __name__ == "__main__":
    asyncio.run(main())
