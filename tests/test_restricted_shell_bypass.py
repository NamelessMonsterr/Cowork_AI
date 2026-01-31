"""
Additional bypass attempt tests for RestrictedShellTool.

Tests sophisticated bypass attempts that attackers might try.
"""

import pytest
from assistant.tools.restricted_shell import RestrictedShellTool, SecurityError


# Test Configuration
ENABLED_CONFIG = {
    "enabled": True,
    "allow_admin": False,
    "timeout_seconds": 30,
    "allowed_cmd": ["dir", "cd", "echo", "ipconfig", "whoami", "ping"],
    "allowed_powershell": ["Get-Process", "Get-Service", "Get-ChildItem"],
    "blocked_patterns": [
        "rm ",
        "del ",
        "rmdir",
        "format",
        "shutdown",
        "Invoke-WebRequest",
        "reg ",
        "taskkill",
        "Remove-Item",
    ],
}


class TestBypassAttempts:
    """Test sophisticated bypass attempts."""

    def test_chain_no_space_ampersand(self):
        """Command chaining without space: dir&&whoami"""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Dangerous character"):
            tool.execute("cmd", "dir&&whoami", run_as_admin=False)

    def test_chain_caret_escape(self):
        """Caret escape bypass attempt: dir ^& whoami"""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Dangerous character"):
            tool.execute("cmd", "dir ^& whoami", run_as_admin=False)

    def test_powershell_semicolon_chain(self):
        """PowerShell semicolon chain: Get-Process; Remove-Item"""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Dangerous character"):
            tool.execute("powershell", "Get-Process; Remove-Item", run_as_admin=False)

    def test_redirect_with_space(self):
        """Output redirect with space: ipconfig > out.txt"""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Dangerous character"):
            tool.execute("cmd", "ipconfig > out.txt", run_as_admin=False)

    def test_dollar_paren_injection(self):
        """PowerShell injection: $([char]65)"""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Dangerous character"):
            tool.execute("powershell", "$([char]65)", run_as_admin=False)

    def test_env_var_expansion(self):
        """%COMSPEC% expansion bypass attempt."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Dangerous character"):
            tool.execute("cmd", "%COMSPEC% /c whoami", run_as_admin=False)

    def test_backtick_escape(self):
        """Backtick escape in PowerShell."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Dangerous character"):
            tool.execute("powershell", "Get-Process `whoami", run_as_admin=False)

    def test_punctuation_bypass_period(self):
        """Punctuation bypass: dir. (should be stripped and allowed)"""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        # This should actually work now because we strip punctuation
        result = tool.execute("cmd", "dir.", run_as_admin=False)
        assert result.exit_code == 0

    def test_punctuation_bypass_exclamation(self):
        """Punctuation bypass: whoami! (should be stripped and allowed)"""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        result = tool.execute("cmd", "whoami!", run_as_admin=False)
        assert result.exit_code == 0

    def test_case_variation(self):
        """Case variation should not bypass: DIR, Dir, dIr"""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        # All should work (case-insensitive)
        result1 = tool.execute("cmd", "DIR", run_as_admin=False)
        assert result1.exit_code == 0

        result2 = tool.execute("cmd", "Dir", run_as_admin=False)
        assert result2.exit_code == 0

        result3 = tool.execute("cmd", "dIr", run_as_admin=False)
        assert result3.exit_code == 0

    def test_extra_spaces(self):
        """Extra spaces should not bypass."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        result = tool.execute("cmd", "  dir  ", run_as_admin=False)
        assert result.exit_code == 0

    def test_blocked_pattern_in_arg(self):
        """Blocked pattern in argument: echo rm /s"""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        # This should be blocked by pattern "rm "
        with pytest.raises(SecurityError, match="Blocked pattern"):
            tool.execute("cmd", "echo rm /s", run_as_admin=False)

    def test_multiline_with_newline(self):
        """Multiline with actual newline character."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Multiline"):
            tool.execute("cmd", "dir\nwhoami", run_as_admin=False)

    def test_multiline_with_carriage_return(self):
        """Multiline with carriage return."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Multiline"):
            tool.execute("cmd", "dir\r\nwhoami", run_as_admin=False)


class TestTimeout:
    """Test timeout enforcement."""

    def test_timeout_enforced(self):
        """Long-running command should timeout."""
        config = {**ENABLED_CONFIG, "timeout_seconds": 1}
        tool = RestrictedShellTool(config)

        # ping with long timeout should exceed 1 second
        with pytest.raises(SecurityError, match="timeout"):
            tool.execute("cmd", "ping -n 10 127.0.0.1", run_as_admin=False)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
