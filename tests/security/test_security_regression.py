"""
Security regression tests to ensure vulnerabilities don't return.
Tests cover all P0 and P1 security issues from the audit.
"""

import pytest
from pathlib import Path

from assistant.utils.input_validator import (
    InputValidator,
    validate_session_permission_request,
)


class TestP0SecurityFixes:
    """Test that P0 critical vulnerabilities remain fixed."""

    def test_no_just_do_it_endpoint(self):
        """Verify /just_do_it bypass endpoint was removed."""
        main_py = Path(__file__).parent.parent / "assistant" / "main.py"
        content = main_py.read_text()

        # Should NOT contain the endpoint decorator
        assert '@app.post("/just_do_it")' not in content
        assert "async def just_do_it" not in content

    def test_no_shell_true_in_code(self):
        """Verify no shell=True subprocess calls."""
        assistant_dir = Path(__file__).parent.parent / "assistant"
        violations = []

        for pyfile in assistant_dir.rglob("*.py"):
            content = pyfile.read_text()
            if "shell=True" in content:
                # Find line numbers
                for i, line in enumerate(content.split("\n"), 1):
                    if "shell=True" in line:
                        violations.append(f"{pyfile}:{i}: {line.strip()}")

        assert not violations, "Found shell=True violations:\n" + "\n".join(violations)

    def test_secrets_enforcement_in_production(self):
        """Verify production mode fails without FLASH_SESSION_SECRET."""
        # This is validated at import time in main.py
        # We verify the code contains the enforcement
        main_py = Path(__file__).parent.parent / "assistant" / "main.py"
        content = main_py.read_text()

        assert "sys.exit(1)" in content
        assert "FLASH_SESSION_SECRET" in content
        assert "IS_PRODUCTION" in content


class TestInputValidation:
    """Test input validation helpers."""

    def test_validate_app_name_whitelist(self):
        """Verify app names are validated against whitelist."""
        # Valid apps
        assert InputValidator.validate_app_name("notepad")[0] == True
        assert InputValidator.validate_app_name("calc")[0] == True
        assert InputValidator.validate_app_name("notepad.exe")[0] == True

        # Invalid apps (not in whitelist)
        assert InputValidator.validate_app_name("hacker.exe")[0] == False
        assert InputValidator.validate_app_name("malicious")[0] == False
        assert InputValidator.validate_app_name("")[0] == False

    def test_validate_file_path_prevents_traversal(self):
        """Verify file path validation prevents directory traversal."""
        # Allowed dirs
        allowed = [r"C:\Users\Public"]

        # Valid path
        valid, msg = InputValidator.validate_file_path(
            r"C:\Users\Public\test.txt", allowed
        )
        assert valid == True

        # Directory traversal attempt
        valid, msg = InputValidator.validate_file_path(
            r"C:\Users\Public\..\..\..\Windows\System32", allowed
        )
        assert valid == False
        assert "outside allowed" in msg.lower()

        # Null byte injection
        valid, msg = InputValidator.validate_file_path("test\x00.txt")
        assert valid == False
        assert "null byte" in msg.lower()

    def test_wildcard_permissions_rejected(self):
        """Verify wildcard (*) permissions are rejected."""
        # Wildcard apps should fail
        valid, msg = validate_session_permission_request(
            apps=["*"], folders=[r"C:\Users\Public"]
        )
        assert valid == False
        assert "wildcard" in msg.lower()

        # Wildcard folders should fail
        valid, msg = validate_session_permission_request(
            apps=["notepad"], folders=["*"]
        )
        assert valid == False
        assert "wildcard" in msg.lower()

    def test_command_sanitization(self):
        """Verify shell metacharacters are removed."""
        dangerous = "notepad & calc"
        sanitized = InputValidator.sanitize_command_arg(dangerous)

        assert "&" not in sanitized
        assert sanitized == "notepad  calc"

        # More dangerous chars
        dangerous2 = "test;rm -rf /|echo 'pwned'"
        sanitized2 = InputValidator.sanitize_command_arg(dangerous2)
        assert ";" not in sanitized2
        assert "|" not in sanitized2


class TestSessionSecurity:
    """Test session security enhancements."""

    def test_session_auth_timer_cleanup(self):
        """Verify SessionAuth properly cleans up timers on revoke."""
        from assistant.safety.session_auth import SessionAuth, SessionManager

        manager = SessionManager()
        auth = SessionAuth(manager=manager, ttl_sec=60)

        # Grant permission
        auth.grant(mode="session", apps={"notepad"}, folders={r"C:\Users\Public"})
        assert auth._expiry_timer is not None
        assert auth.check() == True

        # Revoke should cancel timer
        auth.revoke(reason="test")
        assert auth._expiry_timer is None
        assert auth.check() == False


class TestSecurityDocumentation:
    """Verify security documentation exists."""

    def test_security_md_exists(self):
        """Verify SECURITY.md file exists."""
        security_md = Path(__file__).parent.parent / "SECURITY.md"
        assert security_md.exists(), "SECURITY.md is missing"

        content = security_md.read_text()
        assert "Reporting a Vulnerability" in content
        assert "Security Best Practices" in content

    def test_env_example_no_dangerous_defaults(self):
        """Verify .env.example doesn't enable dangerous defaults."""
        env_example = Path(__file__).parent.parent / ".env.example"
        content = env_example.read_text()

        # Should NOT enable debug endpoints by default
        assert "FLASH_DEV_ENDPOINTS_ENABLED=true" not in content
        assert "ENV=production" in content or "ENV=" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
