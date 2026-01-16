"""
Plugin Permission Manager (W12.5).

Enforces scope-based access control.
Scopes:
- network:<domain>
- secrets:<key>
- clipboard
- filesystem:<path>
"""

import fnmatch
from typing import List, Set

class PermissionManager:
    def __init__(self):
        # Map plugin_id -> set of granted scopes
        self.grants: Dict[str, Set[str]] = {}
        
    def grant(self, plugin_id: str, scopes: List[str]):
        if plugin_id not in self.grants:
            self.grants[plugin_id] = set()
        self.grants[plugin_id].update(scopes)
        
    def check_permission(self, plugin_id: str, required_scope: str) -> bool:
        """Check if plugin has specific permission."""
        granted = self.grants.get(plugin_id, set())
        
        if required_scope in granted:
            return True
            
        # Wildcard support? e.g. network:*.google.com
        # For MVP, simple exact match or prefix for filesystem
        
        return False

    def can_access_secret(self, plugin_id: str, key_name: str) -> bool:
        """Check if secrets:<key> is granted."""
        return self.check_permission(plugin_id, f"secrets:{key_name}")
