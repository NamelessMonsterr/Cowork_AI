import pytest
from assistant.safety.rate_limiter import InputRateLimiter, RateLimitExceededError
import time


def test_rate_limiter_agent_bypass():
    """Verify agent actions bypass rate limits."""
    limiter = InputRateLimiter()

    # Agent should be able to send many keystrokes without triggering limits
    for _ in range(100):
        limiter.record_keystroke(count=1, source="agent")

    # Should not be paused
    assert not limiter._paused, "Agent actions should not trigger rate limits"


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
