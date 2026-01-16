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
from typing import Dict, List, Optional
from assistant.plugins.sdk import Tool, Plugin
from assistant.plugins.manifest import PluginManifest

logger = logging.getLogger("PluginRegistry")

class ToolRegistry:
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.tools: Dict[str, Tool] = {}
        
    def register_plugin(self, manifest: PluginManifest, plugin_instance: Plugin):
        """Register a loaded plugin and its tools."""
        logger.info(f"Registering Plugin: {manifest.id} ({manifest.version})")
        self.plugins[manifest.id] = plugin_instance
        
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

class PluginLoader:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.search_paths = [
            os.path.join(os.getenv('APPDATA'), 'CoworkAI', 'plugins'),
            # Builtins can be added here
        ]
        
    def load_all(self):
        """Scan search paths and load plugins."""
        for path in self.search_paths:
            if not os.path.exists(path):
                continue
                
            # Each folder is a plugin
            for item in os.listdir(path):
                plugin_dir = os.path.join(path, item)
                if os.path.isdir(plugin_dir):
                    self._load_from_dir(plugin_dir)

    def _load_from_dir(self, directory: str):
        manifest_path = os.path.join(directory, "plugin.json")
        if not os.path.exists(manifest_path):
            return
            
        try:
            # 1. Parse Manifest
            with open(manifest_path, 'r') as f:
                data = json.load(f)
            manifest = PluginManifest(**data)
            
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
