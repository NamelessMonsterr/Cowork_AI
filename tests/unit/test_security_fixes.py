import time

import pytest

from assistant.safety.rate_limiter import InputRateLimiter, RateLimitExceededError


def test_rate_limiter_agent_bypass_removed():
    """
    CRITICAL SECURITY FIX: Verify agent actions NO LONGER bypass rate limits.
    
    Previous behavior allowed agent="source" to bypass limits, creating runaway agent risk.
    New secure behavior: ALL actions are rate limited, including agent actions.
    """
    limiter = InputRateLimiter()

    # Agent actions should NOW trigger rate limits (security fix)
    with pytest.raises(RateLimitExceededError):
        for _ in range(200):  # Exceed the limit
            limiter.record_keystroke(count=1, source="agent")

    # Should be paused after hitting hard limit (prevents runaway agent)
    assert limiter._paused, "Agent actions MUST trigger rate limits (security fix)"


def test_rate_limiter_user_enforcement():
    """Verify user actions are subject to rate limits."""
    limiter = InputRateLimiter()

    # User hitting limit should raise exception
    with pytest.raises(RateLimitExceededError):
        for _ in range(200):
            limiter.record_keystroke(count=1, source="user")

    # Should be paused after hitting hard limit
    assert limiter._paused


def test_cleanup_pending_plans_logic():
    """Verify cleanup uses list() for safe iteration."""
    from assistant.main import AppState

    app_state = AppState()
    now = time.time()

    # Setup pending plans with mixed ages
    app_state.pending_plans = {
        "expired_1": (None, now - 400),
        "expired_2": (None, now - 350),
        "valid_1": (None, now - 100),
    }

    # Run cleanup with 300 second TTL
    app_state.cleanup_pending_plans(max_age_seconds=300)

    # Verify expired plans removed, valid plan remains
    assert "expired_1" not in app_state.pending_plans
    assert "expired_2" not in app_state.pending_plans
    assert "valid_1" in app_state.pending_plans
