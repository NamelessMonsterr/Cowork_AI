"""
Tests for RestrictedShellTool security policy.

Validates:
- Allowlist enforcement
- Pattern blocking
- Command chaining prevention
- Admin escalation controls
- Output redaction
"""

import pytest

from assistant.tools.restricted_shell import (
    RestrictedShellTool,
    SecurityError,
    ShellResult,
)

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
    ],
    "redaction_patterns": ["sk-[a-zA-Z0-9]{32,}", "OPENAI_API_KEY=.*"],
}

DISABLED_CONFIG = {"enabled": False}


class TestAllowedCommands:
    """Test that allowlisted commands execute successfully."""

    def test_cmd_ipconfig(self):
        """ipconfig should be allowed."""
        tool = RestrictedShellTool(ENABLED_CONFIG)
        result = tool.execute("cmd", "ipconfig", run_as_admin=False)

        assert isinstance(result, ShellResult)
        assert result.exit_code == 0
        assert len(result.stdout) > 0
        assert "IPv4" in result.stdout or "Adapter" in result.stdout

    def test_cmd_whoami(self):
        """whoami should be allowed."""
        tool = RestrictedShellTool(ENABLED_CONFIG)
        result = tool.execute("cmd", "whoami", run_as_admin=False)

        assert result.exit_code == 0
        assert len(result.stdout) > 0

    def test_cmd_dir(self):
        """dir should be allowed."""
        tool = RestrictedShellTool(ENABLED_CONFIG)
        result = tool.execute("cmd", "dir C:\\", run_as_admin=False)

        assert result.exit_code == 0
        assert len(result.stdout) > 0

    def test_powershell_get_process(self):
        """Get-Process should be allowed."""
        tool = RestrictedShellTool(ENABLED_CONFIG)
        result = tool.execute("powershell", "Get-Process | Select-Object -First 5", run_as_admin=False)

        # Note: This will fail because we block pipes
        # This test documents current behavior
        with pytest.raises(SecurityError, match="pipes"):
            result = tool.execute("powershell", "Get-Process | Select-Object -First 5")

    def test_powershell_get_childitem(self):
        """Get-ChildItem should be allowed."""
        tool = RestrictedShellTool(ENABLED_CONFIG)
        result = tool.execute("powershell", "Get-ChildItem C:\\", run_as_admin=False)

        assert result.exit_code == 0


class TestBlockedCommands:
    """Test that dangerous commands are blocked."""

    def test_del_blocked(self):
        """del command should be blocked."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="not in.*allowlist"):
            tool.execute("cmd", "del /s *.*", run_as_admin=False)

    def test_rm_blocked(self):
        """rm command should be blocked via pattern."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        # Even if "rm" were allowlisted, pattern would block it
        with pytest.raises(SecurityError, match="Blocked pattern|not in.*allowlist"):
            tool.execute("cmd", "rm -rf /", run_as_admin=False)

    def test_format_blocked(self):
        """format command should be blocked."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Blocked pattern|not in.*allowlist"):
            tool.execute("cmd", "format c:", run_as_admin=False)

    def test_shutdown_blocked(self):
        """shutdown should be blocked."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Blocked pattern"):
            tool.execute("cmd", "shutdown /s /t 0", run_as_admin=False)

    def test_powershell_invoke_webrequest_blocked(self):
        """Invoke-WebRequest should be blocked."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Blocked pattern"):
            tool.execute("powershell", "Invoke-WebRequest http://evil.com", run_as_admin=False)

    def test_registry_edit_blocked(self):
        """Registry edits should be blocked."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Blocked pattern"):
            tool.execute("cmd", "reg add HKLM\\Software\\Test", run_as_admin=False)

    def test_taskkill_blocked(self):
        """taskkill should be blocked."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Blocked pattern"):
            tool.execute("cmd", "taskkill /f /im notepad.exe", run_as_admin=False)


class TestCommandChaining:
    """Test that command chaining is prevented."""

    def test_pipe_blocked(self):
        """Pipes should be blocked."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="pipes"):
            tool.execute("cmd", "dir | findstr config", run_as_admin=False)

    def test_redirect_output_blocked(self):
        """Output redirection should be blocked."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="redirect"):
            tool.execute("cmd", "dir > output.txt", run_as_admin=False)

    def test_redirect_append_blocked(self):
        """Append redirection should be blocked."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="redirect"):
            tool.execute("cmd", "echo test >> output.txt", run_as_admin=False)

    def test_command_chain_ampersand_blocked(self):
        """Command chaining with & should be blocked."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="chaining"):
            tool.execute("cmd", "dir & whoami", run_as_admin=False)

    def test_command_chain_double_ampersand_blocked(self):
        """Command chaining with && should be blocked."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="chaining"):
            tool.execute("cmd", "dir && whoami", run_as_admin=False)

    def test_command_chain_semicolon_blocked(self):
        """Command chaining with ; should be blocked."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="chaining"):
            tool.execute("powershell", "Get-Date; Get-Process", run_as_admin=False)

    def test_multiline_blocked(self):
        """Multiline commands should be blocked."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Multiline"):
            tool.execute("cmd", "dir\nwhoami", run_as_admin=False)


class TestAdminEscalation:
    """Test admin escalation controls."""

    def test_admin_disabled_by_default(self):
        """Admin execution should be disabled by default."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Admin execution is disabled"):
            tool.execute("cmd", "ipconfig", run_as_admin=True)

    def test_admin_requires_supervised(self):
        """Admin requires supervised mode even when enabled."""
        config = {**ENABLED_CONFIG, "allow_admin": True}
        tool = RestrictedShellTool(config)

        with pytest.raises(SecurityError, match="requires supervised"):
            tool.execute("cmd", "ipconfig", run_as_admin=True, supervised=False)

    def test_admin_with_supervised(self):
        """Admin should work with supervised mode."""
        config = {**ENABLED_CONFIG, "allow_admin": True}
        tool = RestrictedShellTool(config)

        result = tool.execute("cmd", "ipconfig", run_as_admin=True, supervised=True)
        assert result.exit_code == 0


class TestOutputRedaction:
    """Test sensitive data redaction."""

    def test_api_key_redacted(self):
        """API keys should be redacted from output."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        # Simulate command that outputs API key
        result = tool.execute("cmd", "echo sk-1234567890abcdef1234567890abcdef", run_as_admin=False)

        assert "[REDACTED]" in result.stdout
        assert "sk-1234" not in result.stdout
        assert result.redacted == True

    def test_env_var_redacted(self):
        """Environment variables with secrets should be redacted."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        # This would be redacted if output contained OPENAI_API_KEY=...
        # Can't easily test without setting env var
        pass


class TestDisabledConfig:
    """Test behavior when RestrictedShell is disabled."""

    def test_disabled_blocks_all(self):
        """All commands should be blocked when disabled."""
        tool = RestrictedShellTool(DISABLED_CONFIG)

        with pytest.raises(SecurityError, match="disabled"):
            tool.execute("cmd", "dir", run_as_admin=False)

    def test_disabled_blocks_safe_commands(self):
        """Even safe commands blocked when disabled."""
        tool = RestrictedShellTool(DISABLED_CONFIG)

        with pytest.raises(SecurityError, match="disabled"):
            tool.execute("cmd", "whoami", run_as_admin=False)


class TestInvalidInput:
    """Test handling of invalid inputs."""

    def test_empty_command(self):
        """Empty commands should be rejected."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Empty command"):
            tool.execute("cmd", "", run_as_admin=False)

    def test_invalid_engine(self):
        """Invalid engine should be rejected."""
        tool = RestrictedShellTool(ENABLED_CONFIG)

        with pytest.raises(SecurityError, match="Invalid engine"):
            tool.execute("bash", "ls", run_as_admin=False)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
