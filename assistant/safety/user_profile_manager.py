"""
User Profile Manager - Manages role-based permissions for users.

P1.5 SECURITY ENHANCEMENT: Granular per-user permissions while maintaining
the 9.8/10 security baseline. Supports 5 security tiers from restricted to admin.
"""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """User security profile with permissions."""

    role: str
    description: str
    allowed_apps: list[str]
    allowed_folders: list[str]
    allowed_commands: list[str]
    browser_restrictions: dict[str, Any]
    max_file_size_mb: int
    requires_2fa: bool
    session_timeout_min: int
    can_modify_profiles: bool

    def has_wildcard_apps(self) -> bool:
        """Check if profile allows all apps."""
        return "*" in self.allowed_apps

    def has_wildcard_folders(self) -> bool:
        """Check if profile allows all folders."""
        return "*" in self.allowed_folders

    def has_wildcard_commands(self) -> bool:
        """Check if profile allows all commands."""
        return "*" in self.allowed_commands


class UserProfileManager:
    """
    Manages user security profiles and permissions.

    Security Model:
    - Role-based access control (5 tiers)
    - Global blacklist enforced for ALL users (including admins)
    - Per-user app/folder/command allowlists
    - Fallback to "standard" profile if user not found
    """

    def __init__(self, config_path: str | None = None):
        """
        Initialize profile manager.

        Args:
            config_path: Path to user_profiles.json. If None, loads from default location.
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "user_profiles.json"

        self.config = self._load_config(config_path)
        self.profiles = self.config.get("profiles", {})
        self.user_assignments = self.config.get("user_assignments", {})
        self.global_blacklist = self.config.get("global_blacklist", {})

        logger.info(
            f"[UserProfileManager] Loaded {len(self.profiles)} profiles, "
            f"{len(self.user_assignments)} user assignments"
        )

    def _load_config(self, config_path: Path) -> dict[str, Any]:
        """Load user profiles configuration."""
        try:
            if not config_path.exists():
                logger.warning(f"[UserProfileManager] Config not found: {config_path}")
                return self._get_fallback_config()

            with open(config_path) as f:
                config = json.load(f)
                logger.info(f"[UserProfileManager] Loaded config from {config_path}")
                return config
        except Exception as e:
            logger.error(f"[UserProfileManager] Failed to load config: {e}")
            return self._get_fallback_config()

    def _get_fallback_config(self) -> dict[str, Any]:
        """Return fallback config with just 'standard' profile."""
        return {
            "profiles": {
                "standard": {
                    "role": "standard_user",
                    "description": "Default fallback profile",
                    "allowed_apps": ["notepad", "calc", "chrome"],
                    "allowed_folders": ["%USERPROFILE%\\Documents"],
                    "allowed_commands": ["dir", "echo"],
                    "browser_restrictions": {"domain_whitelist": ["google.com"]},
                    "max_file_size_mb": 10,
                    "requires_2fa": False,
                    "session_timeout_min": 30,
                    "can_modify_profiles": False,
                }
            },
            "user_assignments": {"default": "standard"},
            "global_blacklist": {"commands": [], "apps": []},
        }

    def get_user_profile(self, user_id: str) -> UserProfile:
        """
        Get security profile for specific user.

        Args:
            user_id: User identifier (email, username, etc.)

        Returns:
            UserProfile with user's permissions
        """
        # Look up user's assigned profile
        profile_name = self.user_assignments.get(user_id, self.user_assignments.get("default", "standard"))

        if profile_name not in self.profiles:
            logger.warning(f"[UserProfileManager] Profile '{profile_name}' not found, using 'standard'")
            profile_name = "standard"

        profile_data = self.profiles[profile_name]

        logger.info(f"[UserProfileManager] User '{user_id}' → Profile '{profile_name}'")

        return UserProfile(
            role=profile_data.get("role", "standard_user"),
            description=profile_data.get("description", ""),
            allowed_apps=profile_data.get("allowed_apps", []),
            allowed_folders=profile_data.get("allowed_folders", []),
            allowed_commands=profile_data.get("allowed_commands", []),
            browser_restrictions=profile_data.get("browser_restrictions", {}),
            max_file_size_mb=profile_data.get("max_file_size_mb", 10),
            requires_2fa=profile_data.get("requires_2fa", False),
            session_timeout_min=profile_data.get("session_timeout_min", 30),
            can_modify_profiles=profile_data.get("can_modify_profiles", False),
        )

    def validate_app(self, user_id: str, app: str) -> bool:
        """
        Check if user can launch application.

        Args:
            user_id: User identifier
            app: Application name to validate

        Returns:
            True if user can launch app, False otherwise
        """
        profile = self.get_user_profile(user_id)

        # Check global blacklist first (applies to ALL users)
        if self._is_globally_blacklisted_app(app):
            logger.critical(f"🔴 BLOCKED: App '{app}' in global blacklist (user: {user_id})")
            return False

        # Check if profile has wildcard
        if profile.has_wildcard_apps():
            logger.info(f"✅ ALLOWED: User '{user_id}' has wildcard app permissions")
            return True

        # Check profile's allowed apps
        app_lower = app.lower()
        allowed = any(allowed_app.lower() == app_lower for allowed_app in profile.allowed_apps)

        if allowed:
            logger.info(f"✅ ALLOWED: App '{app}' for user '{user_id}' (profile: {profile.role})")
        else:
            logger.warning(f"🔴 BLOCKED: App '{app}' not in profile for user '{user_id}'")

        return allowed

    def validate_folder(self, user_id: str, path: str) -> bool:
        """
        Check if user can access folder path.

        Args:
            user_id: User identifier
            path: Folder path to validate

        Returns:
            True if user can access folder, False otherwise
        """
        profile = self.get_user_profile(user_id)

        # Wildcard allows all folders
        if profile.has_wildcard_folders():
            return True

        # Expand environment variables in allowed folders
        allowed_folders = [Path(os.path.expandvars(folder)) for folder in profile.allowed_folders]

        try:
            real_path = Path(path).resolve()

            # Check if path is under any allowed folder
            for allowed_folder in allowed_folders:
                try:
                    real_path.relative_to(allowed_folder)
                    return True  # Path is under allowed folder
                except ValueError:
                    continue  # Not under this folder, try next

            logger.warning(f"🔴 BLOCKED: Path '{path}' not in allowed folders for user '{user_id}'")
            return False
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            return False

    def validate_command(self, user_id: str, command: str) -> bool:
        """
        Check if user can execute command.

        Args:
            user_id: User identifier
            command: Command to validate

        Returns:
            True if user can execute command, False otherwise
        """
        profile = self.get_user_profile(user_id)

        # Check global blacklist first
        if self._is_globally_blacklisted_command(command):
            logger.critical(f"🔴 BLOCKED: Command '{command}' in global blacklist (user: {user_id})")
            return False

        # Wildcard allows all commands (except blacklisted)
        if profile.has_wildcard_commands():
            return True

        # Check profile's allowed commands
        command_lower = command.lower()
        allowed = any(allowed_cmd.lower() == command_lower for allowed_cmd in profile.allowed_commands)

        if not allowed:
            logger.warning(f"🔴 BLOCKED: Command '{command}' not in profile for user '{user_id}'")

        return allowed

    def _is_globally_blacklisted_app(self, app: str) -> bool:
        """Check if app is in global blacklist (blocked for ALL users)."""
        blacklisted_apps = self.global_blacklist.get("apps", [])
        return any(app.lower() == blocked.lower() for blocked in blacklisted_apps)

    def _is_globally_blacklisted_command(self, command: str) -> bool:
        """Check if command matches global blacklist patterns."""
        blacklisted_commands = self.global_blacklist.get("commands", [])
        command_lower = command.lower()

        for blocked in blacklisted_commands:
            if blocked.lower() in command_lower:
                return True

        return False

    def get_allowed_folders(self, user_id: str) -> list[Path]:
        """
        Get list of allowed folders for user (expanded environment variables).

        Args:
            user_id: User identifier

        Returns:
            List of Path objects for allowed folders
        """
        profile = self.get_user_profile(user_id)

        if profile.has_wildcard_folders():
            return []  # Empty list means "all folders allowed"

        return [Path(os.path.expandvars(folder)) for folder in profile.allowed_folders]

    def assign_profile(self, user_id: str, profile_name: str) -> bool:
        """
        Assign profile to user (admin only operation).

        Args:
            user_id: User identifier
            profile_name: Name of profile to assign

        Returns:
            True if assignment successful, False if profile doesn't exist
        """
        if profile_name not in self.profiles:
            logger.error(f"Cannot assign non-existent profile '{profile_name}' to user '{user_id}'")
            return False

        self.user_assignments[user_id] = profile_name
        logger.info(f"✅ Assigned profile '{profile_name}' to user '{user_id}'")

        # Note: This doesn't persist to disk - that's handled by API endpoint
        return True
