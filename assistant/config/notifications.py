"""
Notifications Module.

Provides:
- Windows toast notifications
- System tray integration
- Event hooks
"""

import os
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    from win10toast import ToastNotifier
    HAS_TOAST = True
except ImportError:
    HAS_TOAST = False

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False


class NotificationType(str, Enum):
    """Notification types."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    TAKEOVER = "takeover"


@dataclass
class Notification:
    """Notification data."""
    title: str
    message: str
    type: NotificationType = NotificationType.INFO
    duration_sec: int = 5
    sound: bool = True


class NotificationManager:
    """
    Manages Windows notifications.
    
    Features:
    - Toast notifications
    - Sound alerts
    - Callback hooks
    """
    
    SOUNDS = {
        NotificationType.INFO: "SystemAsterisk",
        NotificationType.SUCCESS: "SystemExclamation",
        NotificationType.WARNING: "SystemHand",
        NotificationType.ERROR: "SystemExit",
        NotificationType.TAKEOVER: "SystemHand",
    }
    
    def __init__(self):
        self._toaster = ToastNotifier() if HAS_TOAST else None
        self._callbacks: Dict[NotificationType, list] = {t: [] for t in NotificationType}
        self._enabled = True
    
    @property
    def is_available(self) -> bool:
        return HAS_TOAST
    
    def enable(self):
        self._enabled = True
    
    def disable(self):
        self._enabled = False
    
    def notify(self, notification: Notification):
        """Send a notification."""
        if not self._enabled:
            return
        
        # Play sound
        if notification.sound and HAS_SOUND:
            try:
                winsound.PlaySound(
                    self.SOUNDS.get(notification.type, "SystemAsterisk"),
                    winsound.SND_ALIAS | winsound.SND_ASYNC
                )
            except:
                pass
        
        # Show toast
        if self._toaster:
            try:
                self._toaster.show_toast(
                    notification.title,
                    notification.message,
                    duration=notification.duration_sec,
                    threaded=True,
                )
            except:
                pass
        
        # Call hooks
        for callback in self._callbacks.get(notification.type, []):
            try:
                callback(notification)
            except:
                pass
    
    def info(self, title: str, message: str):
        self.notify(Notification(title, message, NotificationType.INFO))
    
    def success(self, title: str, message: str):
        self.notify(Notification(title, message, NotificationType.SUCCESS))
    
    def warning(self, title: str, message: str):
        self.notify(Notification(title, message, NotificationType.WARNING))
    
    def error(self, title: str, message: str):
        self.notify(Notification(title, message, NotificationType.ERROR))
    
    def takeover(self, message: str):
        self.notify(Notification(
            "Human Takeover Required",
            message,
            NotificationType.TAKEOVER,
            duration_sec=10,
        ))
    
    def on(self, notification_type: NotificationType, callback: Callable):
        """Register callback for notification type."""
        self._callbacks[notification_type].append(callback)
    
    def off(self, notification_type: NotificationType, callback: Callable):
        """Remove callback."""
        if callback in self._callbacks[notification_type]:
            self._callbacks[notification_type].remove(callback)


# Global instance
_notification_manager: Optional[NotificationManager] = None


def get_notifications() -> NotificationManager:
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager
