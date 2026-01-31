"""
IPC Client (W14.2).
Handles communication with the out-of-process Plugin Host.
"""

import os
import json
import logging
import aiohttp
from typing import Dict, Any

logger = logging.getLogger("IpcClient")


class IpcClient:
    def __init__(self):
        self.port_file = os.path.join(
            os.getenv("APPDATA"), "CoworkAI", "plugin_host.json"
        )
        self.host_url = None

    def _refresh_config(self):
        """Read port from file."""
        if not os.path.exists(self.port_file):
            return False

        try:
            with open(self.port_file, "r") as f:
                data = json.load(f)
                self.host_url = f"http://127.0.0.1:{data.get('port')}"
                return True
        except:
            return False

    async def call_tool(
        self, tool_name: str, args: Dict[str, Any], ctx_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tool on host."""
        if not self.host_url:
            if not self._refresh_config():
                raise RuntimeError("Plugin Host not active (port file missing).")

        url = f"{self.host_url}/host/tools/call"
        payload = {"tool_name": tool_name, "args": args, "ctx": ctx_dict}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, timeout=30) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        raise RuntimeError(f"Host Error {resp.status}: {text}")
                    data = await resp.json()
                    return data
            except aiohttp.ClientConnectorError:
                # Retry once after refresh?
                self._refresh_config()
                # Fail for now
                raise RuntimeError("Failed to connect to Plugin Host.")

    async def get_tool_specs(self) -> Dict[str, Any]:
        """Fetch all tool specs from host."""
        if not self.host_url:
            self._refresh_config()
        if not self.host_url:
            return {}

        url = f"{self.host_url}/host/tools/specs"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        return await resp.json()
            except:
                pass
        return {}


from assistant.plugins.sdk import Tool, ToolSpec
from typing import Dict, Any


class RemoteTool(Tool):
    def __init__(self, spec: ToolSpec, client: IpcClient):
        self._spec = spec
        self.client = client

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    async def run(self, args: Dict[str, Any], ctx: Any) -> Dict[str, Any]:
        # Serialize context
        ctx_dict = {"session_id": ctx.session_id, "workspace_path": ctx.workspace_path}
        res = await self.client.call_tool(self._spec.name, args, ctx_dict)
        if res.get("status") == "success":
            return res.get("result")
        else:
            raise RuntimeError(res.get("error", "Unknown remote error"))
