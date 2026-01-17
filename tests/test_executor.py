import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from assistant.executor.executor import ReliableExecutor, ExecutorConfig
from assistant.ui_contracts.schemas import ActionStep, StepResult, VerificationResult
from assistant.safety.budget import ActionBudget, BudgetExceededError
from assistant.safety.session_auth import SessionAuth, PermissionDeniedError
from assistant.executor.strategies.base import Strategy, StrategyResult

class MockStrategy(Strategy):
    def __init__(self, name, priority=1, should_fail=False):
        # Strategy is ABC, no init to call
        self._name = name
        self._priority = priority
        self.should_fail = should_fail
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> int:
        return self._priority

    def can_handle(self, step):
        return True

    def execute(self, step):
        self.call_count += 1
        if self.should_fail:
            return StrategyResult(success=False, error="Mock Failure")
        return StrategyResult(success=True)

class TestReliableExecutor(unittest.TestCase):
    def setUp(self):
        self.auth = MagicMock(spec=SessionAuth)
        self.budget = MagicMock(spec=ActionBudget)
        self.verifier = MagicMock()
        # Provide ALL required fields for VerificationResult
        self.verifier.verify.return_value = VerificationResult(
            success=True,
            verify_type="text_present",
            expected="test",
            duration_ms=100
        )
        self.verifier.capture_state.return_value = {"screenshot": "base64"}
        
        self.step = ActionStep(id="step1", tool="click", args={"target": "btn"})

    def test_execute_success(self):
        """Test simple successful execution."""
        strategy = MockStrategy("success_strat")
        executor = ReliableExecutor([strategy], self.verifier, self.auth, self.budget)
        
        result = executor.execute(self.step)
        
        self.assertTrue(result.success)
        self.assertEqual(result.strategy_used, "success_strat")
        self.auth.ensure.assert_called_once()
        self.budget.check_budget.assert_called_once()

    def test_permission_denied(self):
        """Test failing when session is invalid."""
        self.auth.ensure.side_effect = PermissionDeniedError("No session")
        executor = ReliableExecutor([], self.verifier, self.auth, self.budget)
        
        result = executor.execute(self.step)
        
        self.assertFalse(result.success)
        self.assertIn("No session", result.error)

    def test_budget_exceeded(self):
        """Test failing when budget is exceeded."""
        self.budget.check_budget.side_effect = BudgetExceededError("Day limit", "daily")
        executor = ReliableExecutor([], self.verifier, self.auth, self.budget)
        
        result = executor.execute(self.step)
        
        self.assertFalse(result.success)
        self.assertIn("Day limit", result.error)

    def test_fallback_strategy(self):
        """Test falling back to second strategy."""
        fail_strat = MockStrategy("fail", priority=1, should_fail=True)
        success_strat = MockStrategy("success", priority=2)
        
        executor = ReliableExecutor([fail_strat, success_strat], self.verifier, self.auth, self.budget)
        
        result = executor.execute(self.step)
        
        self.assertTrue(result.success)
        self.assertEqual(result.strategy_used, "success")
        self.assertEqual(fail_strat.call_count, 3) # Retries (default 3)
        self.assertEqual(success_strat.call_count, 1)

    def test_retry_logic(self):
        """Test retries on a single strategy."""
        strat = MockStrategy("retry_strat", should_fail=True)
        config = ExecutorConfig(max_retries_per_strategy=2, retry_delays=[0, 0])
        executor = ReliableExecutor([strat], self.verifier, self.auth, self.budget, config=config)
        
        result = executor.execute(self.step)
        
        self.assertFalse(result.success)
        self.assertEqual(strat.call_count, 2) # 2 attempts based on delay list length/config

if __name__ == '__main__':
    unittest.main()
