"""
Session Manager - Persistent session storage with CSRF protection.

Features:
- Stores sessions in %APPDATA%/CoworkAI/sessions.json
- Hashes session tokens for security
- Manages CSRF tokens
- Handles session expiration and cleanup
"""

import hashlib
import json
import logging
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages persistent session storage and CSRF validation.

    Storage format:
    {
        "sessions": {
            "session_id_hash": {
                "created_at": timestamp,
                "expires_at": timestamp,
                "csrf_token": "token",
                "mode": "session|once",
                "apps": [],
                "folders": []
            }
        }
    }
    """

    def __init__(self, storage_path: str | None = None):
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            app_data = os.getenv("APPDATA")
            if not app_data:
                # Fallback for non-Windows or if var missing
                app_data = os.path.expanduser("~/.coworkai")
            else:
                app_data = os.path.join(app_data, "CoworkAI")

            self.storage_path = Path(app_data) / "sessions.json"

        self._lock = threading.Lock()
        self._ensure_storage_dir()

        # P9 FIX: Auto-recovery - Initialize with backup fallback
        self._initialize_session_data()

    def _initialize_session_data(self):
        """Initialize session data with automatic recovery from backup if needed."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, encoding="utf-8") as f:
                    json.load(f)  # Validate that it's valid JSON
                logger.info("[SessionManager] Session file loaded successfully")
                return
        except json.JSONDecodeError:
            logger.warning("[SessionManager] Main session file corrupt. Attempting recovery from .bak...")
        except Exception as e:
            logger.warning(f"[SessionManager] Failed to read main file: {e}. Checking backup...")

        # Fallback to backup
        backup_path = str(self.storage_path) + ".bak"
        if os.path.exists(backup_path):
            try:
                with open(backup_path, encoding="utf-8") as f:
                    data = json.load(f)

                # Self-healing: Restore main file from validated backup
                with open(self.storage_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

                logger.info("[SessionManager] ✅ Session recovered from .bak and main file restored")
                return
            except Exception as e:
                logger.error(f"[SessionManager] Backup also corrupt: {e}. Starting fresh.")

        # Both failed - start fresh
        logger.warning("[SessionManager] Starting with fresh session state")
        self._write_file({"sessions": {}})

    def _ensure_storage_dir(self):
        """Ensure storage directory exists."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"[SessionManager] Failed to create storage dir: {e}")

    def _hash_token(self, token: str) -> str:
        """Hash token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    def load_session(self, session_id: str) -> dict[str, Any] | None:
        """
        Load a session by ID. Returns session dict if valid, None if not found/expired.
        """
        if not session_id:
            return None

        session_hash = self._hash_token(session_id)

        with self._lock:
            data = self._read_file()
            session = data.get("sessions", {}).get(session_hash)

            if not session:
                return None

            # Check expiry
            if time.time() > session.get("expires_at", 0):
                self._delete_session(session_hash, data)
                return None

            return session

    def save_session(self, session_id: str, permit_data: dict[str, Any], csrf_token: str) -> bool:
        """
        Save a new session or update existing one.
        """
        if not session_id:
            return False

        session_hash = self._hash_token(session_id)

        with self._lock:
            data = self._read_file()

            # Clean up expired sessions first
            self._cleanup_expired(data)

            # Add new session
            data.setdefault("sessions", {})[session_hash] = {
                "created_at": permit_data.get("issued_at", time.time()),
                "expires_at": permit_data.get("expires_at", 0),
                "csrf_token": csrf_token,
                "mode": permit_data.get("mode", "session"),
                "granted_apps": permit_data.get("granted_apps", []),
                "granted_folders": permit_data.get("granted_folders", []),
                "allow_network": permit_data.get("allow_network", False),
            }

            return self._write_file(data)

    def revoke_session(self, session_id: str) -> bool:
        """Revoke a session."""
        if not session_id:
            return False

        session_hash = self._hash_token(session_id)

        with self._lock:
            data = self._read_file()
            if session_hash in data.get("sessions", {}):
                del data["sessions"][session_hash]
                return self._write_file(data)
        return False

    def generate_csrf_token(self) -> str:
        """Generate a secure CSRF token."""
        return secrets.token_urlsafe(32)

    def validate_csrf(self, session_id: str, token: str) -> bool:
        """Validate CSRF token for a given session."""
        session = self.load_session(session_id)
        if not session:
            return False

        stored_token = session.get("csrf_token")
        if not stored_token:
            return False

        return secrets.compare_digest(stored_token, token)

    def _read_file(self) -> dict[str, Any]:
        """Read sessions from disk."""
        if not self.storage_path.exists():
            return {"sessions": {}}

        try:
            with open(self.storage_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[SessionManager] Read error: {e}")
            return {"sessions": {}}

    def _write_file(self, data: dict[str, Any]) -> bool:
        """Write sessions to disk (atomic with backup)."""
        import shutil
        import tempfile

        try:
            # P2 FIX: Atomic write to prevent corruption
            # Write to temp file first, then rename
            dir_name = os.path.dirname(self.storage_path)
            with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
                json.dump(data, tf, indent=2)
                temp_name = tf.name

            # Atomic replacement
            if os.path.exists(self.storage_path):
                os.replace(temp_name, self.storage_path)
            else:
                os.rename(temp_name, self.storage_path)

            # P3 FIX: Quick backup to prevent lockouts
            # P8 FIX: Graceful handling if backup file is locked
            try:
                shutil.copy2(self.storage_path, str(self.storage_path) + ".bak")
            except PermissionError:
                # If backup is locked (e.g., admin has .bak open in Notepad), continue anyway
                logger.warning("[SessionManager] Could not update .bak (File in use?). Main file saved.")

            return True
        except PermissionError as e:
            # P8 FIX: Clearer error for locked files
            logger.error(f"[SessionManager] CRITICAL: Cannot write session file (is it open in another app?): {e}")
            logger.error("[SessionManager] Session changes will be lost on restart!")
            return False
        except Exception as e:
            logger.error(f"[SessionManager] Write error: {e}")
            # Try to clean up temp file if it exists
            try:
                if "temp_name" in locals() and os.path.exists(temp_name):
                    os.remove(temp_name)
            except:
                pass
            return False

    def _cleanup_expired(self, data: dict[str, Any]):
        """Remove expired sessions from data dict (in-place)."""
        now = time.time()
        sessions = data.get("sessions", {})
        expired_hashes = [k for k, v in sessions.items() if now > v.get("expires_at", 0)]

        for k in expired_hashes:
            del sessions[k]

    def _delete_session(self, session_hash: str, data: dict[str, Any]):
        """Delete specific session and save."""
        if session_hash in data.get("sessions", {}):
            del data["sessions"][session_hash]
            self._write_file(data)
