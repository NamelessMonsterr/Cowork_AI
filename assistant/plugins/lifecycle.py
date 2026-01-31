"""
Plugin Lifecycle Management (W13.0).

Handles state definitions and persistence of enabled/disabled plugins.
"""

import json
import logging
import os
from enum import Enum

logger = logging.getLogger("PluginLifecycle")


class PluginState(Enum):
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    BLOCKED_UNTRUSTED = "blocked_untrusted"
    NEEDS_PERMISSION = "needs_permission"
    NEEDS_SECRETS = "needs_secrets"


class PluginStateManager:
    def __init__(self):
        self.config_dir = os.path.join(os.getenv("APPDATA"), "CoworkAI", "plugins")
        self.enabled_file = os.path.join(self.config_dir, "enabled.json")
        self.trusted_file = os.path.join(self.config_dir, "trusted.json")

        self.enabled_plugins: set[str] = set()
        self.trusted_publishers: set[str] = {"CoworkAI Team", "LocalDev"}  # Defaults

        # Ensure dir exists
        os.makedirs(self.config_dir, exist_ok=True)
        self._load()

    def _load(self):
        """Load enabled plugins from JSON."""
        # 1. Load Enabled Plugins
        if os.path.exists(self.enabled_file):
            try:
                with open(self.enabled_file) as f:
                    data = json.load(f)
                    self.enabled_plugins = set(data.get("enabled", []))
            except Exception as e:
                logger.error(f"Failed to load enabled plugins: {e}")

        # 2. Load Trusted Publishers
        if os.path.exists(self.trusted_file):
            try:
                with open(self.trusted_file) as f:
                    data = json.load(f)
                    self.trusted_publishers = set(data.get("trusted", []))
                    self.trusted_publishers.add("CoworkAI Team")  # Always trust host
                    self.trusted_publishers.add("LocalDev")
            except Exception as e:
                logger.error(f"Failed to load trusted publishers: {e}")

    def _save(self):
        """Persist enabled plugins and trusted publishers."""
        try:
            data = {"enabled": list(self.enabled_plugins)}
            with open(self.enabled_file, "w") as f:
                json.dump(data, f, indent=2)

            trust_data = {"trusted": list(self.trusted_publishers)}
            with open(self.trusted_file, "w") as f:
                json.dump(trust_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save plugin config: {e}")

    def is_enabled(self, plugin_id: str) -> bool:
        return plugin_id in self.enabled_plugins

    def enable(self, plugin_id: str):
        self.enabled_plugins.add(plugin_id)
        self._save()

    def disable(self, plugin_id: str):
        if plugin_id in self.enabled_plugins:
            self.enabled_plugins.remove(plugin_id)
            self._save()

    def is_trusted(self, publisher: str) -> bool:
        return publisher in self.trusted_publishers

    def trust_publisher(self, publisher: str):
        self.trusted_publishers.add(publisher)
        self._save()

    def untrust_publisher(self, publisher: str):
        if publisher in self.trusted_publishers:
            self.trusted_publishers.remove(publisher)
            self._save()
