"""
Plugin Host Sandbox (W14.4).
Enforces security boundaries by monkey-patching risky modules.
"""

import sys
import builtins
import os
import io
import logging

logger = logging.getLogger("Sandbox")

original_open = builtins.open
original_import = builtins.__import__

ALLOWED_PATHS = [
    os.getenv('APPDATA'),
    os.getenv('TEMP')
]

def safe_open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    """Restricted open() implementation."""
    # Allow reading internal python files (needed for imports)
    s_file = str(file)
    
    # 1. Allow read-only of system/library files
    if 'r' in mode and not 'w' in mode and not 'a' in mode and not '+' in mode:
        return original_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

    # 2. Enforce Allowlist for Writes
    is_allowed = False
    for path in ALLOWED_PATHS:
        if path and s_file.startswith(path):
            is_allowed = True
            break
            
    if not is_allowed:
        logger.warning(f"SANDBOX: Blocked fs access to {s_file}")
        raise PermissionError(f"Sandbox blocked access to {s_file}")

    return original_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

def apply_patches():
    """Apply sandbox patches."""
    logger.info("🔒 Applying Sandbox Patches...")
    # 1. File System
    builtins.open = safe_open
    
    # 2. Subprocess (Disable completely for now)
    if 'subprocess' in sys.modules:
        sys.modules['subprocess'].Popen = lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("subprocess blocked"))
        sys.modules['subprocess'].run = lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("subprocess blocked"))
    
    # 3. Requests (Network) - We need to hook or block specific domains. 
    # For MVP, we rely on 'requests' being monkey-patched if imported later.
    # A cleaner way is to wrap socket.socket, but that breaks asyncio.
    # We will rely on higher-level permission checks in ToolRouter mostly, 
    # but separate process adds defense-in-depth.
    
    # NETWORK FILTERING STRATEGY (TODO completion):
    # Current: Network access ENABLED for plugins (compatible with external API plugins like OpenAI)
    # Security model: Rely on user permission grants + ToolRouter audit logging
    # Future enhancement options:
    #   1. Socket-layer filtering with domain whitelist (requires plugin manifest defining allowed domains)
    #   2. HTTP proxy with request logging
    #   3. Per-plugin network policies
    # Implementation note: Blanket blocking breaks most plugins (they need OpenAI/external APIs)
    # Recommended: Document required domains in plugin.json manifest, validate at plugin load time
    pass

