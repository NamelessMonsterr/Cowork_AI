"""
Unit tests for PlanGuard Security Policy.

Tests all hardening improvements:
1. Config-driven trusted apps
2. Path normalization
3. drag tool rejection
4. Default-deny unknown tools
5. Expanded blocklist
6. Detailed violation messages
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from assistant.safety.plan_guard import (
    PlanGuard, PlanGuardConfig, PlanValidationError,
    SAFE_TOOLS, BLOCKED_TOOLS, RESTRICTED_SAFE_TOOLS,
    normalize_app_name, load_trusted_apps
)
from assistant.session_auth import SessionAuth
from assistant.ui_contracts.schemas import ActionStep, ExecutionPlan


class TestPlanGuardHardening:
    """Test hardened PlanGuard security policy."""
    
    @pytest.fixture
    def session_auth(self):
        """Create mock session auth."""
        auth = SessionAuth()
        auth.grant("session", 1800)
        return auth
    
    @pytest.fixture
    def plan_guard(self, session_auth):
        """Create PlanGuard instance."""
        return PlanGuard(session_auth)
    
    # Task 1: Config-driven apps
    def test_config_loading(self):
        """Test trusted apps load from config."""
        trusted_apps, aliases = load_trusted_apps()
        assert "notepad" in trusted_apps or "notepad.exe" in trusted_apps
        assert isinstance(aliases, dict)
    
    # Task 2: Path normalization
    def test_path_normalization(self):
        """Test normalize_app_name handles paths correctly."""
        # Full path
        exe, no_ext = normalize_app_name("C:\\Windows\\System32\\notepad.exe")
        assert exe == "notepad.exe"
        assert no_ext == "notepad"
        
        # Whitespace and case
        exe, no_ext = normalize_app_name("  NOTEPAD.EXE  ")
        assert exe == "notepad.exe"
        assert no_ext == "notepad"
        
        # No extension
        exe, no_ext = normalize_app_name("calculator")
        assert exe == "calculator"
        assert no_ext == "calculator"
    
    # Safe commands MUST PASS
    def test_safe_command_calculator(self, plan_guard):
        """✅ Open Calculator - must pass."""
        plan = ExecutionPlan(
            id="test-1",
            task="Open Calculator",
            steps=[
                ActionStep(id="1", tool="open_app", args={"app_name": "calc"}, description="Open calc")
            ]
        )
        
        # Should not raise
        plan_guard.validate(plan)
    
    def test_safe_command_notepad(self, plan_guard):
        """✅ Open Notepad - must pass."""
        plan = ExecutionPlan(
            id="test-2",
            task="Open Notepad",
            steps=[
                ActionStep(id="1", tool="open_app", args={"app_name": "notepad.exe"}, description="Open notepad")
            ]
        )
        
        plan_guard.validate(plan)
    
    def test_safe_command_type_text(self, plan_guard):
        """✅ Type text - must pass."""
        plan = ExecutionPlan(
            id="test-3",
            task="Type hello",
            steps=[
                ActionStep(id="1", tool="type_text", args={"text": "hello"}, description="Type")
            ]
        )
        
        plan_guard.validate(plan)
    
    def test_safe_command_click(self, plan_guard):
        """✅ Click action - must pass."""
        plan = ExecutionPlan(
            id="test-4",
            task="Click",
            steps=[
                ActionStep(id="1", tool="click", args={"x": 100, "y": 200}, description="Click")
            ]
        )
        
        plan_guard.validate(plan)
    
    # Dangerous commands MUST FAIL
    def test_dangerous_command_powershell(self, plan_guard):
        """❌ Open PowerShell - must fail."""
        plan = ExecutionPlan(
            id="test-5",
            task="Open PowerShell",
            steps=[
                ActionStep(id="1", tool="open_app", args={"app_name": "powershell"}, description="Open PS")
            ]
        )
        
        with pytest.raises(PlanValidationError) as exc_info:
            plan_guard.validate(plan)
        
        assert any("not in trusted list" in v.lower() for v in exc_info.value.violations)
        assert len(exc_info.value.violations) > 0
    
    def test_dangerous_command_shell(self, plan_guard):
        """❌ Shell command - must fail."""
        plan = ExecutionPlan(
            id="test-6",
            task="Run shell",
            steps=[
                ActionStep(id="1", tool="run_shell", args={"command": "dir"}, description="Shell")
            ]
        )
        
        with pytest.raises(PlanValidationError) as exc_info:
            plan_guard.validate(plan)
        
        assert any("blocked for safety" in v.lower() for v in exc_info.value.violations)
    
    # Task 4: Unknown tools MUST FAIL
    def test_unknown_tool_rejected(self, plan_guard):
        """❌ Unknown tool - must fail with default-deny."""
        plan = ExecutionPlan(
            id="test-7",
            task="Unknown action",
            steps=[
                ActionStep(id="1", tool="unknown_tool_xyz", args={}, description="Unknown")
            ]
        )
        
        with pytest.raises(PlanValidationError) as exc_info:
            plan_guard.validate(plan)
        
        violations = exc_info.value.violations
        assert any("not recognized" in v.lower() for v in violations)
        assert any("allowed tools" in v.lower() for v in violations)
    
    # Task 3: drag MUST FAIL
    def test_drag_rejected(self, plan_guard):
        """❌ Drag action - must fail (removed from SAFE_TOOLS)."""
        plan = ExecutionPlan(
            id="test-8",
            task="Drag file",
            steps=[
                ActionStep(id="1", tool="drag", args={"from": [0,0], "to": [100,100]}, description="Drag")
            ]
        )
        
        with pytest.raises(PlanValidationError) as exc_info:
            plan_guard.validate(plan)
        
        # drag should now be unrecognized
        violations = exc_info.value.violations
        assert any("not recognized" in v.lower() for v in violations)
    
    # Task 5: Expanded blocklist
    def test_clipboard_blocked(self, plan_guard):
        """❌ Clipboard ops - must fail."""
        plan = ExecutionPlan(
            id="test-9",
            task="Get clipboard",
            steps=[
                ActionStep(id="1", tool="clipboard_get", args={}, description="Clipboard")
            ]
        )
        
        with pytest.raises(PlanValidationError) as exc_info:
            plan_guard.validate(plan)
        
        assert any("blocked for safety" in v.lower() for v in exc_info.value.violations)
    
    def test_file_ops_blocked(self, plan_guard):
        """❌ File operations - must fail."""
        plan = ExecutionPlan(
            id="test-10",
            task="Delete file",
            steps=[
                ActionStep(id="1", tool="delete_file", args={"path": "test.txt"}, description="Delete")
            ]
        )
        
        with pytest.raises(PlanValidationError) as exc_info:
            plan_guard.validate(plan)
        
        assert any("blocked for safety" in v.lower() for v in exc_info.value.violations)
    
    def test_open_url_blocked(self, plan_guard):
        """❌ Open URL - must fail (requires domain allowlist)."""
        plan = ExecutionPlan(
            id="test-11",
            task="Open URL",
            steps=[
                ActionStep(id="1", tool="open_url", args={"url": "http://example.com"}, description="URL")
            ]
        )
        
        with pytest.raises(PlanValidationError) as exc_info:
            plan_guard.validate(plan)
        
        assert any("not in trusted list" in v.lower() for v in exc_info.value.violations)
    
    # Task 6: Detailed violation messages
    def test_violation_messages_detailed(self, plan_guard):
        """❌ Violations include helpful details."""
        plan = ExecutionPlan(
            id="test-12",
            task="Bad app",
            steps=[
                ActionStep(id="1", tool="open_app", args={"app_name": "badapp"}, description="Bad")
            ]
        )
        
        with pytest.raises(PlanValidationError) as exc_info:
            plan_guard.validate(plan)
        
        violations = exc_info.value.violations
        # Should list allowed apps
        assert any("allowed" in v.lower() for v in violations)
        assert any("notepad" in v.lower() or "calc" in v.lower() for v in violations)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
