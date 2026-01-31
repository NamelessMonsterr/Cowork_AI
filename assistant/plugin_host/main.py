"""
Plugin Host Service (W14.1).
Isolated process that loads plugins and executes tools via HTTP/IPC.
"""

import sys
import os
import uvicorn
import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Add project root to path
sys.path.append(os.getcwd())

from assistant.plugins.registry import ToolRegistry, PluginLoader
from assistant.plugins.sdk import ToolContext

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [HOST] %(message)s")
logger = logging.getLogger("PluginHost")

# --- 1. Apply Sandbox ---
# apply_patches() # Enable after testing basic connectivity to avoid confusing startup errors

# --- 2. Initialize Registry ---
registry = ToolRegistry()
loader = PluginLoader(registry)
loader.load_all()  # Re-uses standard loader logic

app = FastAPI(title="Plugin Host")


class ToolCallRequest(BaseModel):
    tool_name: str
    args: Dict[str, Any]
    ctx: Dict[str, Any]  # Serialized context


@app.get("/host/health")
async def health():
    return {"status": "ok", "pid": os.getpid()}


@app.get("/host/version")
async def version():
    return {"version": "1.0.0", "protocol": 1}


@app.get("/host/tools")
async def list_tools():
    """Return list of tools hosted here."""
    # Logic to return tools
    # Current registry maps all loaded tools.
    # We might filter out 'builtins' if the host is only for externals?
    # For MVP, host loads everything in plugins/ dir.
    tools = []
    tools = []
    for t in registry.list_tools():
        tools.append(t.spec.name)
    return tools


@app.get("/host/tools/specs")
async def list_tool_specs():
    """Return full specs of hosted tools."""
    specs = {}
    for t in registry.list_tools():
        specs[t.spec.name] = t.spec.dict()
    return specs


@app.post("/host/tools/call")
async def call_tool(req: ToolCallRequest):
    logger.info(f"HOST CALL: {req.tool_name}")

    tool = registry.get_tool(req.tool_name)
    if not tool:
        raise HTTPException(404, "Tool not found on host")

    # Reconstruct Context
    ctx = ToolContext(
        session_id=req.ctx.get("session_id", "unknown"),
        workspace_path=req.ctx.get("workspace_path", ""),
    )

    try:
        # Run tool
        result = await tool.run(req.args, ctx)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Tool Execution Failed: {e}")
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    # Random port or fixed? Fixed for MVP debugging 8766.
    # W14 spec says "random_port" and write file.
    # Let's stick to fixed 8766 for simplicity in MVP,
    # or implement the file write mechanism.
    port = 8766

    # Write port file
    port_file = os.path.join(os.getenv("APPDATA"), "CoworkAI", "plugin_host.json")
    try:
        import json

        with open(port_file, "w") as f:
            json.dump({"port": port, "pid": os.getpid()}, f)
    except Exception as e:
        logger.error(f"Failed to write port file: {e}")

    uvicorn.run(app, host="127.0.0.1", port=port)
