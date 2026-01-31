"""
Utils Module - Performance and Polish.

Provides:
- Logging with privacy sanitization
- High-performance screen capture
- Plugin permission system
"""

from .capture import (
    HAS_DXCAM,
    HAS_MSS,
    CaptureConfig,
    ScreenCapture,
    get_capture,
)
from .logging import (
    CoworkLogger,
    LogConfig,
    PrivacySanitizer,
    Timer,
    configure_logging,
    get_logger,
    timed,
)
from .permissions import (
    Permission,
    PermissionGrant,
    PermissionManager,
    PluginManifest,
    optional,
    requires,
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
