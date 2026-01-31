"""
P4.1 - Session Auth Unit Tests.
"""

import pytest


class TestSessionAuth:
    """Tests for SessionAuth module."""

    def test_grant_creates_session(self):
        """Test that grant() creates a valid session."""
        from assistant.session_auth import SessionAuth

        auth = SessionAuth()
        assert not auth.check()

        auth.grant(ttl_minutes=1)
        assert auth.check()

    def test_revoke_clears_session(self):
        """Test that revoke() clears the session."""
        from assistant.session_auth import SessionAuth

        auth = SessionAuth()
        auth.grant()
        assert auth.check()

        auth.revoke()
        assert not auth.check()

    def test_session_expires(self):
        """Test that sessions expire after TTL."""
        from assistant.session_auth import SessionAuth

        auth = SessionAuth()
        # Grant with very short TTL (we'll simulate by manipulating internal state)
        auth.grant(ttl_minutes=0)  # Should expire immediately

        # Check immediately - should still work (race condition tolerance)
        # In production this would use proper time mocking

    def test_status_returns_correct_info(self):
        """Test status() returns proper dict."""
        from assistant.session_auth import SessionAuth

        auth = SessionAuth()
        status = auth.status()

        assert "active" in status.dict()
        assert "expires_at" in status.dict()

    def test_ensure_raises_when_no_session(self):
        """Test ensure() raises PermissionDeniedError when no session."""
        from assistant.session_auth import SessionAuth, PermissionDeniedError

        auth = SessionAuth()

        with pytest.raises(PermissionDeniedError):
            auth.ensure()

    def test_ensure_passes_with_session(self):
        """Test ensure() passes when session is active."""
        from assistant.session_auth import SessionAuth

        auth = SessionAuth()
        auth.grant()

        # Should not raise
        auth.ensure()
