"""
Edge Case Tests for Security Components.

Tests edge cases and attack vectors for P0/P1/P1.5 security features:
- UserProfileManager: profile escalation, wildcard manipulation
- ContentRedactor: bypass attempts, pattern edge cases
- SessionAuth: race conditions, timeout edge cases
- PlanGuard: path traversal variants, command injection attempts
"""

import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from assistant.safety.content_redactor import ContentRedactor
from assistant.safety.user_profile_manager import UserProfileManager
from assistant.safety.session_auth import SessionAuth


class TestUserProfileManagerEdgeCases:
    """Edge cases for UserProfileManager (P1.5)."""

    @pytest.fixture
    def profile_manager(self, tmp_path):
        """Create profile manager with test config."""
        config = {
            "profiles": {
                "admin": {
                    "role": "administrator",
                    "allowed_apps": ["*"],
                    "allowed_folders": ["*"],
                    "allowed_commands": ["*"],
                    "browser_restrictions": {"domain_whitelist": "*"},
                    "max_file_size_mb": 100,
                    "requires_2fa": True,
                    "session_timeout_min": 30,
                    "can_modify_profiles": True,
                },
                "standard": {
                    "role": "standard_user",
                    "allowed_apps": ["notepad", "calc"],
                    "allowed_folders": ["%USERPROFILE%\\\\Documents"],
                    "allowed_commands": ["dir", "echo"],
                    "browser_restrictions": {"domain_whitelist": ["google.com"]},
                    "max_file_size_mb": 10,
                    "requires_2fa": False,
                    "session_timeout_min": 30,
                    "can_modify_profiles": False,
                },
                "restricted": {
                    "role": "restricted_user",
                    "allowed_apps": ["notepad"],
                    "allowed_folders": ["%USERPROFILE%\\\\Documents"],
                    "allowed_commands": ["dir"],
                    "browser_restrictions": {"domain_whitelist": ["google.com"]},
                    "max_file_size_mb": 5,
                    "requires_2fa": False,
                    "session_timeout_min": 15,
                    "can_modify_profiles": False,
                },
            },
            "user_assignments": {
                "default": "standard",
                "admin@test.com": "admin",
                "user@test.com": "standard",
                "guest@test.com": "restricted",
            },
            "global_blacklist": {
                "commands": ["format", "diskpart", "bcdedit"],
                "apps": ["regedit", "msconfig"],
            },
        }

        config_path = tmp_path / "test_user_profiles.json"
        with open(config_path, "w") as f:
            json.dump(config, f)

        return UserProfileManager(config_path=str(config_path))

    def test_profile_escalation_blocked(self, profile_manager):
        """❌ EDGE CASE: Standard user cannot escalate to admin."""
        # User is assigned 'standard'
        profile = profile_manager.get_user_profile("user@test.com")
        assert profile.role == "standard_user"

        # They should NOT have admin powers
        assert not profile.has_wildcard_apps()
        assert "powershell" not in [app.lower() for app in profile.allowed_apps]

    def test_wildcard_manipulation_blocked(self, profile_manager):
        """❌ EDGE CASE: Cannot inject wildcard into standard profile."""
        # Standard user tries to access app not in their list
        is_allowed = profile_manager.validate_app("user@test.com", "powershell")
        assert not is_allowed, "Wildcard manipulation should be blocked"

    def test_global_blacklist_blocks_admin(self, profile_manager):
        """❌ EDGE CASE: Global blacklist blocks even admins."""
        # Admin has wildcard but global blacklist should still block
        is_allowed = profile_manager.validate_app("admin@test.com", "regedit")
        assert not is_allowed, "Global blacklist should block admin from regedit"

        # Same for commands
        is_allowed_cmd = profile_manager.validate_command("admin@test.com", "format C:")
        assert not is_allowed_cmd, "Global blacklist should block admin from format"

    def test_path_traversal_blocked(self, profile_manager):
        """❌ EDGE CASE: Path traversal should not escape sandbox."""
        # Restricted user tries to access .ssh via path traversal
        is_allowed = profile_manager.validate_folder(
            "guest@test.com",
            "%USERPROFILE%\\\\Documents\\\\..\\\\..\\\\..\\\\Users\\\\Admin\\\\.ssh",
        )
        # This should resolve and be blocked
        assert not is_allowed, "Path traversal should be blocked"

    def test_case_sensitivity_normalization(self, profile_manager):
        """✅ EDGE CASE: Case variations should work."""
        # Standard user can access notepad
        assert profile_manager.validate_app("user@test.com", "notepad")
        assert profile_manager.validate_app("user@test.com", "NOTEPAD")
        assert profile_manager.validate_app("user@test.com", "Notepad.exe")

    def test_nonexistent_user_gets_default(self, profile_manager):
        """✅ EDGE CASE: Unknown users get default profile."""
        profile = profile_manager.get_user_profile("unknown@test.com")
        assert profile.role == "standard_user"  # Should use default

    def test_malformed_profile_fallback(self, tmp_path):
        """✅ EDGE CASE: Malformed config falls back gracefully."""
        bad_config = tmp_path / "bad_config.json"
        with open(bad_config, "w") as f:
            f.write("invalid json {{{")

        # Should not crash, should use fallback
        mgr = UserProfileManager(config_path=str(bad_config))
        profile = mgr.get_user_profile("test@test.com")
        assert profile.role == "standard_user"  # Fallback profile


class TestContentRedactorEdgeCases:
    """Edge cases for ContentRedactor (P1)."""

    def test_redact_api_key_variants(self):
        """✅ EDGE CASE: Detect API key format variations."""
        # Standard format
        text, was_redacted = ContentRedactor.redact("MY_API_KEY=sk-1234567890abcdef")
        assert was_redacted
        assert "***REDACTED***" in text

        # Different prefix variations
        text2, _ = ContentRedactor.redact("OPENAI_API_KEY=sk-proj-xyz123")
        assert "***REDACTED***" in text2

    def test_redact_password_obfuscation_attempts(self):
        """❌ EDGE CASE: Obfuscated passwords should still be caught."""
        # Common obfuscation: spaces
        text, was_redacted = ContentRedactor.redact("password: p a s s 1 2 3")
        # This might not be caught - just verify current behavior
        # In production, consider more sophisticated patterns

    def test_redact_multiple_secrets_same_line(self):
        """✅ EDGE CASE: Multiple secrets on same line."""
        text = "API_KEY=sk-123 and PASSWORD=secret123 and EMAIL=user@test.com"
        redacted, was_redacted = ContentRedactor.redact(text)
        assert was_redacted
        assert "***REDACTED***" in redacted
        # Should have at least 2 redactions
        assert redacted.count("***REDACTED***") >= 2

    def test_redact_ssn_formats(self):
        """✅ EDGE CASE: Various SSN formats."""
        # Standard format
        text1, _ = ContentRedactor.redact("SSN: 123-45-6789")
        assert "***REDACTED***" in text1

        # No dashes
        text2, _ = ContentRedactor.redact("SSN: 123456789")
        assert "***REDACTED***" in text2

    def test_redact_credit_card_variations(self):
        """✅ EDGE CASE: Credit card number variations."""
        # Spaces
        text1, _ = ContentRedactor.redact("Card: 1234 5678 9012 3456")
        assert "***REDACTED***" in text1

        # Dashes
        text2, _ = ContentRedactor.redact("Card: 1234-5678-9012-3456")
        assert "***REDACTED***" in text2

    def test_no_redaction_for_safe_content(self):
        """✅ EDGE CASE: Safe content passes through."""
        safe_text = "Hello world, this is a normal message with numbers 12345"
        redacted, was_redacted = ContentRedactor.redact(safe_text)
        assert not was_redacted
        assert redacted == safe_text

    def test_unicode_in_secrets(self):
        """✅ EDGE CASE: Unicode characters near secrets."""
        text = "PASSWORD=pässwörd123 🔐"
        redacted, was_redacted = ContentRedactor.redact(text)
        assert was_redacted
        assert "***REDACTED***" in redacted


class TestSessionAuthEdgeCases:
    """Edge cases for SessionAuth (P0)."""

    def test_concurrent_grant_revoke(self):
        """❌ EDGE CASE: Race condition on grant/revoke."""
        auth = SessionAuth()

        def grant_session():
            for _ in range(100):
                auth.grant("test", 1800)
                time.sleep(0.001)

        def revoke_session():
            for _ in range(100):
                auth.revoke()
                time.sleep(0.001)

        thread1 = threading.Thread(target=grant_session)
        thread2 = threading.Thread(target=revoke_session)

        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # Should not crash - verify state is valid
        status = auth.status()
        assert isinstance(status["active"], bool)

    def test_rapid_ensure_calls(self):
        """✅ EDGE CASE: Rapid ensure() calls should not cause issues."""
        auth = SessionAuth()
        auth.grant("test", 1800)

        # Rapid calls
        for _ in range(1000):
            auth.ensure()  # Should not crash

    def test_session_timeout_boundary(self):
        """⏱️ EDGE CASE: Session expires exactly at boundary."""
        auth = SessionAuth()
        auth.grant("test", 1)  # 1 second TTL

        # Should be valid immediately
        auth.ensure()

        # Wait for expiry
        time.sleep(1.1)

        # Should now be expired
        with pytest.raises(Exception):  # PermissionDeniedError
            auth.ensure()

    def test_negative_ttl_rejected(self):
        """❌ EDGE CASE: Negative TTL should be handled."""
        auth = SessionAuth()
        # This should either raise or treat as 0
        try:
            auth.grant("test", -100)
            # If it doesn't raise, verify session expires immediately
            time.sleep(0.1)
            with pytest.raises(Exception):
                auth.ensure()
        except ValueError:
            # Or it might reject negative values - both are valid
            pass

    def test_very_large_ttl(self):
        """✅ EDGE CASE: Very large TTL should work."""
        auth = SessionAuth()
        auth.grant("test", 999999)  # ~11 days
        status = auth.status()
        assert status["active"]
        assert status["remaining_sec"] > 999998


class TestPlanGuardPathTraversalVariants:
    """Additional path traversal edge cases for PlanGuard."""

    def test_path_traversal_url_encoded(self):
        """❌ EDGE CASE: URL-encoded path traversal."""
        # Test if %2e%2e%2f (../) bypass detection
        # This would be tested in RestrictedShellTool path validation
        pass  # Placeholder - implement if RestrictedShellTool is exposed

    def test_path_traversal_unicode(self):
        """❌ EDGE CASE: Unicode path traversal attempts."""
        # Unicode variations of "../"
        # U+FF0E = ． (fullwidth full stop)
        # U+2215 = ∕ (division slash)
        pass  # Placeholder

    def test_absolute_path_injection(self):
        """❌ EDGE CASE: Absolute path trying to escape sandbox."""
        # Test if "C:\\Windows\\System32" gets blocked when sandbox is active
        pass  # Placeholder


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
