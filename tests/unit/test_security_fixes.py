import pytest
import os
import json
import tempfile
import pathlib
from unittest import mock
import unicodedata

from assistant.safety.plan_guard import PlanGuard, PlanGuardConfig, PlanValidationError
from assistant.safety.shell_validator import RestrictedShellValidator
from assistant.tools.restricted_shell import RestrictedShellTool
from assistant.safety.session_manager import SessionManager
from assistant.voice.audio_recorder import AudioRecorder, AudioError
from assistant.ui_contracts.schemas import ExecutionPlan, ActionStep

# ==================== P0-1 PlanGuard Tests ====================

class TestPlanGuardSecurity:
    
    @pytest.fixture
    def guard(self):
        config = PlanGuardConfig(
            allowed_tools=["open_url"],
            trusted_domains=["example.com", "docs.python.org", "api.github.com"]
        )
        mock_auth = mock.Mock()
        return PlanGuard(mock_auth, config)
        
    def _create_plan(self, steps_data):
        steps = []
        for i, (tool, args) in enumerate(steps_data):
            steps.append(ActionStep(
                id=f"step_{i}", 
                tool=tool, 
                args=args
            ))
        return ExecutionPlan(
            id="test_plan",
            task="security test",
            steps=steps
        )

    def test_block_ip_addresses(self, guard):
        """Verify that IP addresses (IPv4/IPv6) are blocked."""
        # IPv4
        plan = self._create_plan([("open_url", {"url": "http://1.1.1.1"})])
        
        with pytest.raises(PlanValidationError) as excinfo:
            guard.validate(plan)
        assert any("IP addresses are not allowed" in v for v in excinfo.value.violations)

        # IPv4 Localhost
        plan = self._create_plan([("open_url", {"url": "http://127.0.0.1"})])
        with pytest.raises(PlanValidationError):
            guard.validate(plan)
        
        # IPv6
        plan = self._create_plan([("open_url", {"url": "http://[::1]"})])
        with pytest.raises(PlanValidationError):
            guard.validate(plan)
        
    def test_domain_allowlist(self, guard):
        # Allowed exact match
        plan = self._create_plan([("open_url", {"url": "https://example.com/foo"})])
        guard.validate(plan)  # Should not raise
        
        # Allowed subdomain match
        plan = self._create_plan([("open_url", {"url": "https://sub.docs.python.org"})])
        guard.validate(plan)  # Should not raise

        # Blocked domain
        plan = self._create_plan([("open_url", {"url": "https://evil.com"})])
        with pytest.raises(PlanValidationError) as excinfo:
            guard.validate(plan)
        assert any("not in trusted list" in v for v in excinfo.value.violations)

        # Blocked deceptive subdomain (e.g. evil-example.com)
        plan = self._create_plan([("open_url", {"url": "https://evil-example.com"})])
        with pytest.raises(PlanValidationError):
            guard.validate(plan)


# ==================== P0-2 Restricted Shell Tests ====================

class TestRestrictedShellSecurity:
    
    def test_shell_validator_blocking(self):
        validator = RestrictedShellValidator()
        
        # Blocked patterns
        assert not validator.validate("cmd", "echo hello | other")
        assert not validator.validate("cmd", "echo hello > file")
        assert not validator.validate("powershell", "Invoke-Expression 'bad'")
        assert not validator.validate("powershell", "iex 'bad'")
        
        # Blocked flags
        assert not validator.validate("powershell", "powershell -enc CAMDAA...")
        
        # Unicode normalization check
        # '＞' is FULLWIDTH GREATER-THAN SIGN (U+FF1E) which normalizes to '>'
        assert not validator.validate("cmd", "echo hello \uff1e file")
        
    def test_tool_integration(self):
        config = {
            "enabled": True,
            "allow_admin": False,
            "allowed_commands": {"cmd": ["echo"], "powershell": ["Write-Host"]}
        }
        tool = RestrictedShellTool(config)
        
        # Should pass
        tool._validate_command("cmd", "echo hello", False, False)
        
        # Should fail (pipe)
        with pytest.raises(Exception):
            tool._validate_command("cmd", "echo hello | whoami", False, False)


# ==================== P1-3 Session Persistence Tests ====================

class TestSessionManager:
    
    def test_session_lifecycle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Override session path for testing
            mock_path = pathlib.Path(temp_dir) / "sessions.json"
            
            with mock.patch("assistant.safety.session_manager.SESSION_FILE", mock_path):
                manager = SessionManager()
                
                # Create session
                session_id = manager.create_session("test_mode", 30)
                assert session_id
                
                # Verify persistence
                assert mock_path.exists()
                with open(mock_path) as f:
                    data = json.load(f)
                    assert session_id in data
                
                # Verify CSRF
                csrf = manager.get_csrf_token(session_id)
                assert csrf
                assert manager.validate_csrf(session_id, csrf)
                assert not manager.validate_csrf(session_id, "invalid")
                
                # Revoke
                manager.revoke_session(session_id)
                with open(mock_path) as f:
                    data = json.load(f)
                    assert session_id not in data


# ==================== P1-4 Audio Recorder Tests ====================

class TestAudioRecorderErrorHandling:
    
    @mock.patch("assistant.voice.audio_recorder.sd")
    def test_device_not_found(self, mock_sd):
        mock_sd.query_devices.side_effect = Exception("No audio device found")
        
        recorder = AudioRecorder()
        # Should not crash on init, but record should fail
        
        data, error = recorder.record(1)
        assert data is None
        assert error is not None
        assert error["code"] == "device_error"

    @mock.patch("assistant.voice.audio_recorder.sd")
    def test_record_success(self, mock_sd):
        import numpy as np
        # Mock successful recording
        mock_sd.rec.return_value = np.zeros((16000, 1), dtype='float32')
        mock_sd.wait.return_value = None
        
        recorder = AudioRecorder()
        data, error = recorder.record(1)
        
        assert error is None
        assert data is not None
        assert len(data) > 0
