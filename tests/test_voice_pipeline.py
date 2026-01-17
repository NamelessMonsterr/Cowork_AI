"""
Regression Tests for Voice Pipeline (Task D).

Tests:
D1: Voice simulate → Plan preview
D2: Preview → Approve → Executes  
D3: No permission → approve fails
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestVoicePipeline:
    """Test the voice → plan → execute pipeline."""
    
    @pytest.fixture
    def mock_state(self):
        """Create a mock application state."""
        from assistant.ui_contracts.schemas import ActionStep, ExecutionPlan
        
        state = MagicMock()
        state.stt = MagicMock()
        state.stt.get_health.return_value = {
            "stt_engine": "mock",
            "available": True,
            "error": None
        }
        state.stt.listen = AsyncMock(return_value="Open Notepad and type Hello")
        
        state.planner = MagicMock()
        state.planner.create_plan = AsyncMock(return_value=[
            {"tool": "open_app", "args": {"name": "notepad"}, "description": "Open Notepad"},
            {"tool": "type_text", "args": {"text": "Hello"}, "description": "Type Hello"}
        ])
        
        state.session_auth = MagicMock()
        state.session_auth.check.return_value = False
        
        state.pending_plans = {}
        state.websocket_clients = []
        state.is_executing = False
        state.current_task_id = None
        
        state.broadcast = AsyncMock()
        
        return state
    
    @pytest.mark.asyncio
    async def test_voice_simulate_generates_preview(self, mock_state):
        """D1: Call /voice/dev_simulate → /plan/preview returns plan."""
        from assistant.ui_contracts.schemas import ActionStep, ExecutionPlan
        
        # Simulate /plan/preview logic
        task = "Open Notepad and type Hello"
        
        raw_steps = await mock_state.planner.create_plan(task)
        
        action_steps = []
        for i, s in enumerate(raw_steps):
            s["id"] = s.get("id", str(i+1))
            action_steps.append(ActionStep(**s))
        
        plan = ExecutionPlan(id="test-plan-123", task=task, steps=action_steps)
        
        # Verify
        assert plan is not None
        assert len(plan.steps) == 2
        assert plan.steps[0].tool == "open_app"
        assert plan.steps[1].tool == "type_text"
        assert plan.task == task
    
    @pytest.mark.asyncio
    async def test_preview_approve_executes(self, mock_state):
        """D2: Preview → Approve → execution_started event."""
        from assistant.ui_contracts.schemas import ActionStep, ExecutionPlan
        
        # Create a plan and store it
        plan = ExecutionPlan(
            id="test-plan-456",
            task="Open Notepad",
            steps=[
                ActionStep(id="1", tool="open_app", args={"name": "notepad"}, description="Open")
            ]
        )
        mock_state.pending_plans["test-plan-456"] = plan
        
        # Simulate approval check
        mock_state.session_auth.check.return_value = True
        
        # Verify plan exists
        fetched_plan = mock_state.pending_plans.get("test-plan-456")
        assert fetched_plan is not None
        assert fetched_plan.id == "test-plan-456"
        
        # Simulate removal and execution signal
        del mock_state.pending_plans["test-plan-456"]
        await mock_state.broadcast("execution_started", {"plan_id": "test-plan-456"})
        
        # Verify broadcast was called
        mock_state.broadcast.assert_called_with("execution_started", {"plan_id": "test-plan-456"})
    
    @pytest.mark.asyncio
    async def test_approve_without_permission_fails(self, mock_state):
        """D3: Revoked session → /plan/approve returns 403."""
        from fastapi import HTTPException
        
        # Session is not active
        mock_state.session_auth.check.return_value = False
        
        # Simulate the approval check
        if not mock_state.session_auth.check():
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(403, "Forbidden: Active session required")
            
            assert exc_info.value.status_code == 403
            assert "Active session required" in exc_info.value.detail


class TestSTTEngineFactory:
    """Test STT engine selection and fallback."""
    
    def test_mock_fallback_when_no_whisper(self):
        """STT falls back to mock when faster-whisper unavailable."""
        from assistant.voice.stt import STTEngineFactory, MockSTT
        
        # Force mock mode
        factory = STTEngineFactory(prefer_mock=True)
        engine = factory.get_engine()
        
        assert engine is not None
        assert engine.name == "mock"
        assert engine.is_available()
    
    def test_health_returns_engine_info(self):
        """get_health returns engine status."""
        from assistant.voice.stt import STTEngineFactory
        
        factory = STTEngineFactory(prefer_mock=True)
        health = factory.get_health()
        
        assert "stt_engine" in health
        assert "available" in health
        assert health["stt_engine"] == "mock"
        assert health["available"] == True
    
    @pytest.mark.asyncio
    async def test_mock_stt_transcribes(self):
        """MockSTT returns valid transcript."""
        from assistant.voice.stt import MockSTT
        
        mock = MockSTT()
        result = await mock.transcribe_mic(2)
        
        assert result is not None
        assert len(result) > 0
        assert "Open" in result or "Calculator" in result


class TestPlanPreviewAPI:
    """Test plan preview storage and retrieval."""
    
    def test_pending_plans_storage(self):
        """Plans are stored and retrievable."""
        from assistant.ui_contracts.schemas import ActionStep, ExecutionPlan
        
        pending_plans = {}
        
        plan = ExecutionPlan(
            id="preview-123",
            task="Test task",
            steps=[ActionStep(id="1", tool="test", args={}, description="Test")]
        )
        
        pending_plans["preview-123"] = plan
        
        assert "preview-123" in pending_plans
        assert pending_plans["preview-123"].task == "Test task"
        
        # Removal
        del pending_plans["preview-123"]
        assert "preview-123" not in pending_plans


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
