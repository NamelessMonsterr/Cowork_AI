"""
Failure Classifier - Maps errors to Recovery Types (W9.2).
"""

from enum import Enum
from typing import Tuple

class FailureType(Enum):
    ELEMENT_NOT_FOUND = "element_not_found"
    WINDOW_NOT_FOCUSED = "window_not_focused"
    WINDOW_CHANGED = "window_changed"
    APP_NOT_RUNNING = "app_not_running"
    VERIFY_FAILED = "verify_failed"
    NETWORK_TIMEOUT = "network_timeout"
    BLOCKED_BY_UAC = "blocked_by_uac"
    SENSITIVE_SCREEN = "sensitive_screen"
    PERMISSION_REQUIRED = "permission_required"
    UNKNOWN = "unknown"

class FailureClassifier:
    
    @staticmethod
    def classify(error_msg: str) -> Tuple[FailureType, bool]:
        """
        Classify error message into Type and Recoverability.
        Returns: (FailureType, is_recoverable)
        """
        msg = error_msg.lower()
        
        if "access denied" in msg or "uac" in msg or "elevation" in msg:
            return FailureType.BLOCKED_BY_UAC, False
            
        if "secure desktop" in msg or "sensitive" in msg:
            return FailureType.SENSITIVE_SCREEN, False
            
        if "permission" in msg:
            return FailureType.PERMISSION_REQUIRED, False
            
        if "element not found" in msg or "timeout waiting for element" in msg or "selector" in msg:
            return FailureType.ELEMENT_NOT_FOUND, True
            
        if "window" in msg and ("not found" in msg or "active" in msg):
            return FailureType.WINDOW_NOT_FOCUSED, True
            
        if "verification failed" in msg:
            return FailureType.VERIFY_FAILED, True
            
        if "process" in msg and "not running" in msg:
            return FailureType.APP_NOT_RUNNING, True
            
        return FailureType.UNKNOWN, False
