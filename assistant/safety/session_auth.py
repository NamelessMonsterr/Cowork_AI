"""
Session Permission Gate - Every run requires explicit consent.

This module ensures that no automation occurs without user permission.
Sessions expire on: timeout, app close, screen lock, or manual revoke.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Literal, Optional, Callable
from enum import Enum


class PermissionMode(str, Enum):
    """Permission grant modes."""

    SESSION = "session"  # Allow for duration of session (default 30 min)
    ONCE = "once"  # Allow for single task only
    DENIED = "denied"  # Explicitly denied


@dataclass
class SessionPermit:
    """
    Represents the current permission state.

    Attributes:
        allowed: Whether actions are currently allowed
        mode: The permission mode (session, once, denied)
        granted_apps: List of allowed application names
        granted_folders: List of allowed folder paths
        allow_network: Whether network access is permitted
        issued_at: Unix timestamp when permission was granted
        expires_at: Unix timestamp when permission expires
        task_completed: For 'once' mode, tracks if task is done
        csrf_token: Unique token for CSRF protection
    """

    allowed: bool = False
    mode: PermissionMode = PermissionMode.DENIED
    granted_apps: list[str] = field(default_factory=list)
    granted_folders: list[str] = field(default_factory=list)
    allow_network: bool = False
    issued_at: float = 0
    expires_at: float = 0
    task_completed: bool = False
    csrf_token: Optional[str] = None


class PermissionDeniedError(Exception):
    """Raised when an action is attempted without valid permission."""

    pass


class SessionExpiredError(PermissionDeniedError):
    """Raised when session has expired."""

    pass


class SessionAuth:
    """
    Session-based permission gate for all automation actions.

    Usage:
        session = SessionAuth(ttl_sec=1800)  # 30 minutes

        # User grants permission via UI
        session.grant(mode="session", apps=["chrome", "notepad"])

        # Before any action:
        session.ensure()  # Raises if not permitted

        # Revoke on exit, lock, or user request
        session.revoke()
    """

    DEFAULT_TTL_SEC = 30 * 60  # 30 minutes
    DEFAULT_APPS = ["notepad", "chrome", "vscode", "explorer", "terminal"]
    DEFAULT_FOLDERS = ["Documents", "Downloads", "Desktop"]
    SESSION_ID = "current_session"  # Single session ID for now

    def __init__(
        self,
        ttl_sec: int = DEFAULT_TTL_SEC,
        on_expire: Optional[Callable[[], None]] = None,
        on_revoke: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize SessionAuth.

        Args:
            ttl_sec: Session timeout in seconds (default: 30 minutes)
            on_expire: Callback when session expires
            on_revoke: Callback when session is manually revoked
        """
        self._ttl_sec = ttl_sec
        self._permit = SessionPermit()
        self._lock = threading.Lock()
        self._on_expire = on_expire
        self._on_revoke = on_revoke
        self._expiry_timer: Optional[threading.Timer] = None

        # Initialize session manager
        from .session_manager import SessionManager

        self._manager = SessionManager()

        # Try to load existing session
        self._load_saved_session()

    def _load_saved_session(self):
        """Load session from disk if valid."""
        saved = self._manager.load_session(self.SESSION_ID)
        if saved:
            with self._lock:
                now = time.time()
                self._permit = SessionPermit(
                    allowed=True,
                    mode=PermissionMode(saved["mode"]),
                    granted_apps=saved["granted_apps"],
                    granted_folders=saved["granted_folders"],
                    allow_network=saved["allow_network"],
                    issued_at=saved["created_at"],
                    expires_at=saved["expires_at"],
                    csrf_token=saved["csrf_token"],
                )

                # Restore timer
                remaining = saved["expires_at"] - now
                if remaining > 0:
                    self._expiry_timer = threading.Timer(
                        remaining, self._on_auto_expire
                    )
                    self._expiry_timer.daemon = True
                    self._expiry_timer.start()

    @property
    def permit(self) -> SessionPermit:
        """Get current permit (read-only snapshot)."""
        with self._lock:
            return SessionPermit(
                allowed=self._permit.allowed,
                mode=self._permit.mode,
                granted_apps=self._permit.granted_apps.copy(),
                granted_folders=self._permit.granted_folders.copy(),
                allow_network=self._permit.allow_network,
                issued_at=self._permit.issued_at,
                expires_at=self._permit.expires_at,
                task_completed=self._permit.task_completed,
                csrf_token=self._permit.csrf_token,
            )

    def check(self) -> bool:
        """
        Check whether there is an active session without raising.
        Returns True if allowed and not expired; False otherwise.
        """
        with self._lock:
            if not self._permit.allowed:
                return False

            now = time.time()
            if now > self._permit.expires_at:
                return False

            return True

    def grant(
        self,
        mode: Literal["session", "once"] = "session",
        apps: Optional[list[str]] = None,
        folders: Optional[list[str]] = None,
        allow_network: bool = False,
        ttl_override: Optional[int] = None,
    ) -> None:
        """
        Grant permission for the session.

        Args:
            mode: "session" (time-limited) or "once" (single task)
            apps: Allowed applications (None = use defaults)
            folders: Allowed folders (None = use defaults)
            allow_network: Whether to allow network/web actions
            ttl_override: Override default TTL for this grant
        """
        now = time.time()
        ttl = ttl_override if ttl_override is not None else self._ttl_sec

        # Generate CSRF token
        csrf_token = self._manager.generate_csrf_token()

        with self._lock:
            # Cancel existing timer
            if self._expiry_timer:
                self._expiry_timer.cancel()

            self._permit = SessionPermit(
                allowed=True,
                mode=PermissionMode(mode),
                granted_apps=apps if apps is not None else self.DEFAULT_APPS.copy(),
                granted_folders=folders
                if folders is not None
                else self.DEFAULT_FOLDERS.copy(),
                allow_network=allow_network,
                issued_at=now,
                expires_at=now + ttl,
                task_completed=False,
                csrf_token=csrf_token,
            )

            # Save to disk
            permit_dict = {
                "issued_at": now,
                "expires_at": now + ttl,
                "mode": mode,
                "granted_apps": self._permit.granted_apps,
                "granted_folders": self._permit.granted_folders,
                "allow_network": allow_network,
            }
            self._manager.save_session(self.SESSION_ID, permit_dict, csrf_token)

            # Set expiry timer
            self._expiry_timer = threading.Timer(ttl, self._on_auto_expire)
            self._expiry_timer.daemon = True
            self._expiry_timer.start()

    def revoke(self, reason: str = "manual") -> None:
        """
        Revoke current permission.

        Args:
            reason: Why permission was revoked (for logging)
        """
        with self._lock:
            was_allowed = self._permit.allowed

            if self._expiry_timer:
                self._expiry_timer.cancel()
                self._expiry_timer = None

            self._permit = SessionPermit()  # Reset to default (denied)
            self._manager.revoke_session(self.SESSION_ID)

        # Log security event
        if was_allowed:
            audit = get_security_logger()
            audit.log_auth_revoke(reason)

        if was_allowed and self._on_revoke:
            self._on_revoke()

    def validate_csrf(self, token: str) -> bool:
        """Validate CSRF token against current session."""
        with self._lock:
            if not self._permit.allowed:
                return False
            return self._manager.validate_csrf(self.SESSION_ID, token)

    def ensure(self) -> None:
        """
        Ensure session is valid. Must be called before any automation action.

        Raises:
            PermissionDeniedError: If no permission granted
            SessionExpiredError: If session has expired
        """
        with self._lock:
            if not self._permit.allowed:
                raise PermissionDeniedError("Session permission not granted.")

            now = time.time()
            if now > self._permit.expires_at:
                self._permit.allowed = False
                raise SessionExpiredError("Session permission has expired.")

            # Check if 'once' mode and task already completed
            if self._permit.mode == PermissionMode.ONCE and self._permit.task_completed:
                raise PermissionDeniedError("Single-task permission already used.")

    def is_app_allowed(self, app_name: str) -> bool:
        """Check if an application is in the allowed list."""
        with self._lock:
            if not self._permit.allowed:
                return False
            return app_name.lower() in [a.lower() for a in self._permit.granted_apps]

    def is_folder_allowed(self, folder_path: str) -> bool:
        """
        Check if folder is in granted folders.
        P4 FIX: Protected against path traversal attacks.
        """
        import os

        if not folder_path:
            return False

        with self._lock:
            if not self._permit.allowed:
                return False

            # P4 FIX: Normalize the path to prevent traversal (../) attacks
            try:
                normalized_path = os.path.realpath(os.path.abspath(folder_path))
            except (ValueError, OSError):
                # Invalid path syntax
                return False

            # Check against granted folders (also normalized)
            for granted_folder in self._permit.granted_folders:
                try:
                    normalized_granted = os.path.realpath(
                        os.path.abspath(granted_folder)
                    )
                    # Check if the path starts with any granted folder
                    if normalized_path.startswith(normalized_granted):
                        return True
                except (ValueError, OSError):
                    continue

            return False

    def is_network_allowed(self) -> bool:
        """Check if network access is permitted."""
        with self._lock:
            return self._permit.allowed and self._permit.allow_network

    def time_remaining(self) -> int:
        """Return seconds remaining until session expires. Returns 0 if expired or not allowed."""
        with self._lock:
            if not self._permit.allowed:
                return 0
            remaining = self._permit.expires_at - time.time()
            return max(0, int(remaining))

    def mark_task_completed(self) -> None:
        """Mark the current task as completed (relevant for 'once' mode)."""
        with self._lock:
            self._permit.task_completed = True
            if self._permit.mode == PermissionMode.ONCE:
                self._permit.allowed = False
                self._manager.revoke_session(self.SESSION_ID)

    def extend(self, additional_sec: int) -> None:
        """
        Extend the current session.

        Args:
            additional_sec: Seconds to add to expiry time
        """
        with self._lock:
            if not self._permit.allowed:
                return

            self._permit.expires_at += additional_sec

            # Reset timer
            if self._expiry_timer:
                self._expiry_timer.cancel()

            remaining = self._permit.expires_at - time.time()
            if remaining > 0:
                self._expiry_timer = threading.Timer(remaining, self._on_auto_expire)
                self._expiry_timer.daemon = True
                self._expiry_timer.start()

    def _on_auto_expire(self) -> None:
        """Called when session expires automatically."""
        with self._lock:
            self._permit.allowed = False

        if self._on_expire:
            self._on_expire()

    def get_status_dict(self) -> dict:
        """Get status as dictionary for UI display."""
        permit = self.permit
        return {
            "allowed": permit.allowed,
            "mode": permit.mode.value if permit.mode else "denied",
            "granted_apps": permit.granted_apps,
            "granted_folders": permit.granted_folders,
            "allow_network": permit.allow_network,
            "time_remaining_sec": self.time_remaining(),
            "expires_at_iso": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.localtime(permit.expires_at)
            )
            if permit.expires_at > 0
            else None,
            "csrf_token": permit.csrf_token,
        }
