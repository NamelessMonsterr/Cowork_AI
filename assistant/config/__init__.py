"""Configuration module for Cowork AI Assistant."""

from .settings import Settings, get_settings
from .manager import (
    AppConfig, UIConfig, SafetyConfig, VoiceConfig, PerformanceConfig,
    ConfigManager, get_config,
)
from .notifications import (
    Notification, NotificationType, NotificationManager, get_notifications,
)

__all__ = [
    "Settings", "get_settings",
    "AppConfig", "UIConfig", "SafetyConfig", "VoiceConfig", "PerformanceConfig",
    "ConfigManager", "get_config",
    "Notification", "NotificationType", "NotificationManager", "get_notifications",
]
