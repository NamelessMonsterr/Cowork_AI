"""
Plugin Permission System (Future-Ready).

Provides:
- Permission declarations for plugins
- Capability-based access control
- Sandboxing preparation
"""

from typing import List, Set, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class Permission(str, Enum):
    """Available permissions for plugins."""
    # File system
    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    FILE_DELETE = "file:delete"
    
    # Network
    NETWORK_HTTP = "network:http"
    NETWORK_WEBSOCKET = "network:websocket"
    
    # System
    PROCESS_SPAWN = "process:spawn"
    PROCESS_KILL = "process:kill"
    
    # UI
    UI_CLICK = "ui:click"
    UI_TYPE = "ui:type"
    UI_SCREENSHOT = "ui:screenshot"
    
    # Clipboard
    CLIPBOARD_READ = "clipboard:read"
    CLIPBOARD_WRITE = "clipboard:write"
    
    # Voice
    VOICE_LISTEN = "voice:listen"
    VOICE_SPEAK = "voice:speak"
    
    # Admin
    ADMIN_ELEVATED = "admin:elevated"
    ADMIN_REGISTRY = "admin:registry"


@dataclass
class PluginManifest:
    """Plugin manifest declaring permissions and metadata."""
    name: str
    version: str
    description: str
    author: str
    permissions: List[Permission] = field(default_factory=list)
    optional_permissions: List[Permission] = field(default_factory=list)
    
    def requires(self, permission: Permission) -> bool:
        return permission in self.permissions
    
    def can_request(self, permission: Permission) -> bool:
        return permission in self.optional_permissions


@dataclass  
class PermissionGrant:
    """Record of granted permissions."""
    plugin_name: str
    granted: Set[Permission] = field(default_factory=set)
    denied: Set[Permission] = field(default_factory=set)
    granted_at: float = 0.0
    expires_at: Optional[float] = None


class PermissionManager:
    """
    Manages plugin permissions.
    
    Future-ready for:
    - Plugin sandboxing
    - User approval flow
    - Permission expiry
    """
    
    def __init__(self):
        self._grants: Dict[str, PermissionGrant] = {}
        self._default_grants: Set[Permission] = {
            Permission.UI_SCREENSHOT,
            Permission.UI_CLICK,
            Permission.UI_TYPE,
        }
    
    def register_plugin(self, manifest: PluginManifest) -> PermissionGrant:
        """Register a plugin and create initial grant."""
        grant = PermissionGrant(
            plugin_name=manifest.name,
            granted=self._default_grants.intersection(set(manifest.permissions)),
        )
        self._grants[manifest.name] = grant
        return grant
    
    def check_permission(self, plugin_name: str, permission: Permission) -> bool:
        """Check if plugin has permission."""
        grant = self._grants.get(plugin_name)
        if not grant:
            return False
        return permission in grant.granted
    
    def grant_permission(self, plugin_name: str, permission: Permission):
        """Grant a permission to a plugin."""
        if plugin_name in self._grants:
            self._grants[plugin_name].granted.add(permission)
    
    def revoke_permission(self, plugin_name: str, permission: Permission):
        """Revoke a permission from a plugin."""
        if plugin_name in self._grants:
            self._grants[plugin_name].granted.discard(permission)
            self._grants[plugin_name].denied.add(permission)
    
    def get_grant(self, plugin_name: str) -> Optional[PermissionGrant]:
        """Get permission grant for a plugin."""
        return self._grants.get(plugin_name)
    
    def list_plugins(self) -> List[str]:
        """List registered plugins."""
        return list(self._grants.keys())


# ==================== Decorators ====================

def requires(*permissions: Permission):
    """Decorator to check permissions before function execution."""
    def decorator(func):
        func._required_permissions = list(permissions)
        return func
    return decorator


def optional(*permissions: Permission):
    """Decorator to mark optional permissions."""
    def decorator(func):
        func._optional_permissions = list(permissions)
        return func
    return decorator
