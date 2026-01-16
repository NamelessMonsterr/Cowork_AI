"""
Utils Module - Performance and Polish.

Provides:
- Logging with privacy sanitization
- High-performance screen capture
- Plugin permission system
"""

from .logging import (
    CoworkLogger,
    LogConfig,
    PrivacySanitizer,
    Timer,
    timed,
    get_logger,
    configure_logging,
)

from .capture import (
    ScreenCapture,
    CaptureConfig,
    get_capture,
    HAS_DXCAM,
    HAS_MSS,
)

from .permissions import (
    Permission,
    PluginManifest,
    PermissionGrant,
    PermissionManager,
    requires,
    optional,
)

__all__ = [
    # Logging
    "CoworkLogger",
    "LogConfig", 
    "PrivacySanitizer",
    "Timer",
    "timed",
    "get_logger",
    "configure_logging",
    
    # Capture
    "ScreenCapture",
    "CaptureConfig",
    "get_capture",
    "HAS_DXCAM",
    "HAS_MSS",
    
    # Permissions
    "Permission",
    "PluginManifest",
    "PermissionGrant", 
    "PermissionManager",
    "requires",
    "optional",
]
