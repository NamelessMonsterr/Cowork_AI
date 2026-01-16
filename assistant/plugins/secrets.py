"""
Plugin Secrets Manager (W12.4).

Provides isolated secret storage for plugins.
Storage Format: Namespaced keys (e.g. cowork.plugin.id.key)
"""

from typing import Optional
# Reusing main SecretsManager logic or independent?
# For now independent MVP adapter.

class PluginSecrets:
    def __init__(self):
        # In real app, this would use keyring or encrypted DB
        self._storage = {} 
        
    def set(self, plugin_id: str, key: str, value: str):
        full_key = f"cowork.plugin.{plugin_id}.{key}"
        self._storage[full_key] = value
        
    def get(self, plugin_id: str, key: str) -> Optional[str]:
        full_key = f"cowork.plugin.{plugin_id}.{key}"
        return self._storage.get(full_key)
