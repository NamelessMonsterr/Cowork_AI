"""
Plugin Registry & Loader (W12.2).

Responsibilities:
1. Discover plugins in search paths.
2. Load plugin.json manifests.
3. Import plugin modules safely.
4. Register tools in a central registry.
"""

import os
import json
import logging
import importlib.util
from typing import Dict, List, Optional, Any
from assistant.plugins.sdk import Tool, Plugin, ToolSpec
from assistant.plugins.manifest import PluginManifest

TRUSTED_PUBLISHERS = {"CoworkAI Team", "LocalDev"}

logger = logging.getLogger("PluginRegistry")


class ToolRegistry:
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.manifests: Dict[str, PluginManifest] = {}
        self.tools: Dict[str, Tool] = {}

    def register_plugin(self, manifest: PluginManifest, plugin_instance: Plugin):
        """Register a loaded plugin and its tools."""
        logger.info(f"Registering Plugin: {manifest.id} ({manifest.version})")
        self.plugins[manifest.id] = plugin_instance
        self.manifests[manifest.id] = manifest

        tools = plugin_instance.get_tools()
        for tool in tools:
            if tool.spec.name in self.tools:
                logger.warning(f"Overwriting existing tool: {tool.spec.name}")
            self.tools[tool.spec.name] = tool
            logger.debug(f"Registered Tool: {tool.spec.name}")

    def get_tool(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def list_tools(self) -> List[Tool]:
        return list(self.tools.values())

    def get_manifest(self, plugin_id: str) -> Optional[PluginManifest]:
        return self.manifests.get(plugin_id)


class PluginLoader:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.search_paths = [
            os.path.join(os.getenv("APPDATA"), "CoworkAI", "plugins"),
            # Builtins can be added here
        ]

    def load_all(self):
        """Load builtins and local plugins (for Host process)."""
        self.load_builtins()
        self.load_externals()

    def load_builtins(self):
        builtin_dir = os.path.join(os.path.dirname(__file__), "builtins")
        self._load_from_dir(builtin_dir)

    def load_externals(self):
        plugins_dir = os.path.join(os.getenv("APPDATA"), "CoworkAI", "plugins")
        self._load_from_dir(plugins_dir)

    async def load_from_host(self, ipc_client: Any):
        """Load remote tools from Plugin Host."""
        # We need to import RemoteTool dynamically to avoid top-level loop
        from assistant.plugins.ipc import RemoteTool

        specs = await ipc_client.get_tool_specs()
        for name, spec_data in specs.items():
            spec = ToolSpec(**spec_data)
            logger.info(f"Registering Remote Tool: {name}")

            tool_instance = RemoteTool(spec, ipc_client)
            self.registry.tools[name] = tool_instance

    def _load_from_dir(self, directory: str):
        manifest_path = os.path.join(directory, "plugin.json")
        if not os.path.exists(manifest_path):
            return

        try:
            # 1. Parse Manifest
            with open(manifest_path, "r") as f:
                data = json.load(f)
            manifest = PluginManifest(**data)

            # W12 Trust Check
            if manifest.publisher not in TRUSTED_PUBLISHERS:
                logger.warning(
                    f"⚠️ Plugin '{manifest.name}' has untrusted publisher: '{manifest.publisher}'. Loading anyway for Dev."
                )
                # allowed = False
                # if not allowed: return

            # 2. Import Module
            # Entrypoint format: "module_file:ClassName"
            mod_name, class_name = manifest.entrypoint.split(":")
            module_file = os.path.join(directory, f"{mod_name}.py")

            spec = importlib.util.spec_from_file_location(mod_name, module_file)
            if not spec or not spec.loader:
                raise ImportError(f"Could not load module {module_file}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 3. Instantiate Plugin
            plugin_cls = getattr(module, class_name)
            plugin_instance = plugin_cls()

            if not isinstance(plugin_instance, Plugin):
                raise TypeError(f"{class_name} is not a Plugin instance")

            # 4. Register
            self.registry.register_plugin(manifest, plugin_instance)

        except Exception as e:
            logger.error(f"Failed to load plugin from {directory}: {e}")
