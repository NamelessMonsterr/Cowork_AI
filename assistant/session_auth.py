import time
from dataclasses import dataclass, field
from typing import List

@dataclass
class SessionPermit:
    allowed: bool = False
    mode: str = "session"  # "session" or "once"
    granted_apps: List[str] = field(default_factory=list)
    granted_folders: List[str] = field(default_factory=list)
    issued_at: float = 0
    expires_at: float = 0

class SessionAuth:
    def __init__(self, ttl_sec: int = 30*60):
        self.ttl_sec = ttl_sec
        self.permit = SessionPermit()

    def grant(self, mode="session", ttl_sec=None, apps=None, folders=None):
        """Grant a new session permit."""
        now = time.time()
        ttl = ttl_sec if ttl_sec is not None else self.ttl_sec
        self.permit = SessionPermit(
            allowed=True,
            mode=mode,
            granted_apps=apps or [],
            granted_folders=folders or [],
            issued_at=now,
            expires_at=now + ttl,
        )

    def revoke(self):
        """Revoke the current session."""
        self.permit = SessionPermit()

    def ensure(self):
        """Raise PermissionError if session invalid or expired."""
        now = time.time()
        if not self.permit.allowed:
            raise PermissionError("Session permission not granted")
        if now > self.permit.expires_at:
            self.revoke() # Auto-revoke on expiry
            raise PermissionError("Session expired")

    def time_remaining(self) -> int:
        """Return remaining seconds in session."""
        if not self.permit.allowed:
            return 0
        return max(0, int(self.permit.expires_at - time.time()))

    def check(self) -> bool:
        """Return True if session is active and valid (non-raising)."""
        try:
            self.ensure()
            return True
        except PermissionError:
            return False

    def status(self):
        """Return status dict/object for API."""
        return SessionStatus(
            allowed=self.check(),
            time_remaining=self.time_remaining(),
            mode=self.permit.mode
        )

@dataclass
class SessionStatus:
    allowed: bool
    time_remaining: int
    mode: str
    
    def dict(self):
        return {
            "allowed": self.allowed,
            "time_remaining": self.time_remaining,
            "mode": self.mode
        }
