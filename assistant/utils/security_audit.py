"""
Security audit logger for tracking sensitive operations and potential threats.
"""

import logging
import json
import time
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SecurityAuditLogger:
    """Centralized security event logging."""
    
    # Security event types
    EVENT_AUTH_GRANT = "auth.grant"
    EVENT_AUTH_REVOKE = "auth.revoke"
    EVENT_AUTH_CHECK_FAILED = "auth.check_failed"
    EVENT_COMMAND_EXECUTED = "command.executed"
    EVENT_FILE_ACCESS = "file.access"
    EVENT_SUSPICIOUS_INPUT = "input.suspicious"
    EVENT_CONFIG_CHANGE = "config.change"
    EVENT_SESSION_EXPIRED = "session.expired"
    
    def __init__(self):
        self.security_logger = logging.getLogger("security_audit")
        # Ensure security logs go to separate handler in production
        self.security_logger.setLevel(logging.INFO)
    
    def log_event(
        self,
        event_type: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Log a security event.
        
        Args:
            event_type: Type of security event (use EVENT_* constants)
            success: Whether the operation succeeded
            details: Additional context
            user_id: User identifier (if applicable)
            ip_address: Client IP address (if applicable)
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "success": success,
            "user_id": user_id or "unknown",
            "ip_address": ip_address or "unknown",
            "details": details or {}
        }
        
        # Log as JSON for easy parsing
        self.security_logger.info(json.dumps(event))
        
        # Also log to main logger for visibility
        level = logging.INFO if success else logging.WARNING
        msg = f"Security Event: {event_type} - {'SUCCESS' if success else 'FAILED'}"
        if details:
            msg += f" - {details}"
        logger.log(level, msg)
    
    def log_auth_grant(self, mode: str, apps: set, folders: set) -> None:
        """Log permission grant event."""
        self.log_event(
            self.EVENT_AUTH_GRANT,
            success=True,
            details={
                "mode": mode,
                "apps_count": len(apps),
                "folders_count": len(folders),
                "wildcard_apps": "*" in apps,
                "wildcard_folders": "*" in folders
            }
        )
    
    def log_auth_revoke(self, reason: str) -> None:
        """Log permission revoke event."""
        self.log_event(
            self.EVENT_AUTH_REVOKE,
            success=True,
            details={"reason": reason}
        )
    
    def log_auth_check_failed(self, resource_type: str, resource_name: str) -> None:
        """Log failed permission check (potential unauthorized access attempt)."""
        self.log_event(
            self.EVENT_AUTH_CHECK_FAILED,
            success=False,
            details={
                "resource_type": resource_type,
                "resource_name": resource_name
            }
        )
    
    def log_command_executed(self, command_type: str, target: str, success: bool) -> None:
        """Log command execution."""
        self.log_event(
            self.EVENT_COMMAND_EXECUTED,
            success=success,
            details={
                "command_type": command_type,
                "target": target[:100]  # Truncate for privacy
            }
        )
    
    def log_file_access(self, operation: str, file_path: str, success: bool) -> None:
        """Log file system access."""
        self.log_event(
            self.EVENT_FILE_ACCESS,
            success=success,
            details={
                "operation": operation,
                "file_path": file_path[:200]  # Truncate
            }
        )
    
    def log_suspicious_input(self, input_type: str, reason: str, sample: str) -> None:
        """Log potentially malicious input detected."""
        self.log_event(
            self.EVENT_SUSPICIOUS_INPUT,
            success=False,
            details={
                "input_type": input_type,
                "reason": reason,
                "sample": sample[:50]  # Limited sample for analysis
            }
        )


# Global instance
_audit_logger: Optional[SecurityAuditLogger] = None


def get_security_logger() -> SecurityAuditLogger:
    """Get the global security audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = SecurityAuditLogger()
    return _audit_logger
