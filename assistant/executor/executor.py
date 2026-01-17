"""
Reliable Executor - Core execution engine with multi-strategy fallback.

This is the heart of the agent's action execution:
1. Check session permission
2. Capture before state
3. Try strategies in priority order with retries
4. Verify action succeeded
5. Log result
6. Escalate to takeover if all fail

The executor ensures reliability through:
- Multiple fallback strategies
- Exponential backoff retries
- Verification after every action
- Budget tracking
- Environment safety checks
"""

import time
import logging
from typing import List, Optional, Callable
from dataclasses import dataclass

from assistant.ui_contracts.schemas import (
    ActionStep,
    StepResult,
    VerificationResult,
    UISelector,
)
from assistant.safety.session_auth import SessionAuth, PermissionDeniedError
from assistant.safety.budget import ActionBudget, BudgetExceededError
from assistant.safety.environment import EnvironmentMonitor, EnvironmentState
from .strategies.base import Strategy, StrategyResult
from .cache import SelectorCache
from .verify import Verifier

# W20.3 Learning Integration (Optional)
try:
    from assistant.learning.ranker import StrategyRanker
    from assistant.learning.collector import LearningCollector
    HAS_LEARNING = True
except ImportError:
    HAS_LEARNING = False
    StrategyRanker = None
    LearningCollector = None

from assistant.safety.focus_guard import FocusGuard, FocusLostError
from assistant.safety.rate_limiter import InputRateLimiter, RateLimitExceededError


logger = logging.getLogger(__name__)


@dataclass
class ExecutorConfig:
    """Configuration for ReliableExecutor."""
    max_retries_per_strategy: int = 3
    retry_delays: list[float] = None  # Exponential backoff delays
    verify_timeout_sec: int = 5
    action_timeout_sec: int = 30  # Timeout per action
    capture_screenshots: bool = True
    use_selector_cache: bool = True
    safe_mode: bool = False  # If True, blocks destructive actions
    
    def __post_init__(self):
        if self.retry_delays is None:
            self.retry_delays = [0.5, 1.0, 2.0]  # Exponential backoff


class ReliableExecutor:
    """
    Multi-strategy executor with verification and safety checks.
    
    Usage:
        executor = ReliableExecutor(
            strategies=[uia_strategy, ocr_strategy, vision_strategy, coords_strategy],
            verifier=verifier,
            session_auth=session_auth,
            budget=budget,
            environment=environment_monitor,
            cache=selector_cache,
        )
        
        result = executor.execute(step)
        if not result.success:
            if result.requires_takeover:
                # Request human intervention
            else:
                # Handle error
    """



    def __init__(
        self,
        strategies: List[Strategy],
        verifier: Verifier,
        session_auth: SessionAuth,
        budget: ActionBudget,
        environment: Optional[EnvironmentMonitor] = None,
        cache: Optional[SelectorCache] = None,
        config: Optional[ExecutorConfig] = None,
        on_takeover_required: Optional[Callable[[str], None]] = None,
        on_step_complete: Optional[Callable[[StepResult], None]] = None,
        # V24 Safety
        focus_guard: Optional[FocusGuard] = None,
        rate_limiter: Optional[InputRateLimiter] = None,
        # W20.3 Learning
        ranker: Optional["StrategyRanker"] = None,
        collector: Optional["LearningCollector"] = None,
    ):
        """
        Initialize ReliableExecutor.
        """
        self._strategies = sorted(strategies, key=lambda s: s.priority)
        self._verifier = verifier
        self._session = session_auth
        self._budget = budget
        self._environment = environment
        self._cache = cache or SelectorCache()
        self._config = config or ExecutorConfig()
        self._on_takeover = on_takeover_required
        self._on_step_complete = on_step_complete
        
        # V24 Safety Components
        self._focus_guard = focus_guard
        self._rate_limiter = rate_limiter
        
        self._is_paused = False
        self._pause_reason = ""
        
        # W20.3: Learning Components (Optional)
        self._ranker = ranker
        self._collector = collector

    def execute(self, step: ActionStep) -> StepResult:
        """
        Execute an action step with full safety and reliability.
        
        Args:
            step: The action step to execute
            
        Returns:
            StepResult with execution details
        """
        start_time = time.time()
        screenshot_before = None
        screenshot_after = None
        
        DESTRUCTIVE_TOOLS = ["delete_file", "kill_process", "format_disk"]
        
        try:
            # 1. Check paused state
            if self._is_paused:
                return self._make_failed_result(
                    step, start_time,
                    error=f"Executor paused: {self._pause_reason}",
                    requires_takeover=True,
                    takeover_reason=self._pause_reason,
                )
            
            # 1.5 Safe Mode Check (V24)
            if self._config.safe_mode and step.tool in DESTRUCTIVE_TOOLS:
                return self._make_failed_result(
                    step, start_time,
                    error=f"Action blocked by Safe Mode: {step.tool}",
                    requires_takeover=True,
                    takeover_reason="Destructive action blocked by Safe Mode",
                )
            
            # 2. Check session permission
            try:
                self._session.ensure()
            except PermissionDeniedError as e:
                return self._make_failed_result(
                    step, start_time,
                    error=str(e),
                    requires_takeover=True,
                    takeover_reason="Session permission required",
                )
            
            # 3. Check budget
            try:
                self._budget.check_budget()
            except BudgetExceededError as e:
                return self._make_failed_result(
                    step, start_time,
                    error=str(e),
                    requires_takeover=True,
                    takeover_reason=f"Budget exceeded: {e.budget_type}",
                )
            
            # 4. Check environment safety
            if self._environment:
                env_state = self._environment.check_state()
                if env_state != EnvironmentState.NORMAL:
                    reason = f"Unsafe environment: {env_state.value}"
                    return self._make_failed_result(
                        step, start_time,
                        error=reason,
                        requires_takeover=True,
                        takeover_reason=reason,
                    )

            # 4.5 Safety Hardening (V24)
            # Check Focus
            if self._focus_guard:
                focus_res = self._focus_guard.check_focus()
                if not focus_res.is_focused:
                    return self._make_failed_result(
                        step, start_time,
                        error=f"Focus lost: {focus_res.error or 'Active window mismatch'}",
                        requires_takeover=True,
                        takeover_reason="Focus Guard: Execution paused due to focus loss",
                    )
            
            # Check Rate Limit
            if self._rate_limiter:
                try:
                    if step.tool in ["type_text", "press_key"]:
                        count = 1
                        if step.tool == "type_text" and "text" in step.args:
                            count = len(step.args["text"])
                        self._rate_limiter.record_keystroke(count)
                    elif step.tool in ["click", "double_click", "right_click"]:
                        self._rate_limiter.record_click()
                except RateLimitExceededError as e:
                    return self._make_failed_result(
                        step, start_time,
                        error=str(e),
                        requires_takeover=True,
                        takeover_reason=f"Rate Limiter: {str(e)}",
                    )
            
            # 5. Capture before state
            before_state = self._verifier.capture_state()
            screenshot_before = before_state.get("screenshot")
            
            # 6. Check selector cache
            cache_key = None
            if self._config.use_selector_cache:
                current_title = ""
                if hasattr(self._verifier, "_computer") and self._verifier._computer:
                    win = self._verifier._computer.get_active_window()
                    if win:
                        current_title = win.title
                        
                cache_key = self._cache.generate_key(step.tool, step.args, current_title)
                cached = self._cache.get(cache_key)
                if cached:
                    step.selector = cached
                    logger.debug(f"Using cached selector for {cache_key}")
            
            # 7. Try strategies in priority order (W20.3: Use Ranker if available)
            last_error = None
            strategy_used = None
            selector_to_cache = None
            
            # Extract app name from window title for learning
            app_name = None
            if current_title:
                # Simple heuristic: Use the last part of title or process name
                # In production, we'd get actual process name from Computer
                parts = current_title.split(" - ")
                app_name = parts[-1].lower() if parts else "unknown"
            
            # W20.3: Reorder strategies based on learned success rates
            ordered_strategies = self._strategies
            if self._ranker and app_name:
                strategy_order = self._ranker.get_strategy_order(app_name)
                # Reorder self._strategies to match
                name_to_strat = {s.name: s for s in self._strategies}
                ordered_strategies = [name_to_strat[n] for n in strategy_order if n in name_to_strat]
                # Add any strategies not in the order (safety)
                for s in self._strategies:
                    if s not in ordered_strategies:
                        ordered_strategies.append(s)

            for strategy in ordered_strategies:
                if not strategy.can_handle(step):
                    continue
                
                strategy_used = strategy.name
                
                # Try with retries
                for attempt, delay in enumerate(self._config.retry_delays):
                    if attempt > 0:
                        time.sleep(delay)
                        self._budget.record_action(success=False, was_retry=True)
                    
                    try:
                        result = strategy.execute(step)
                        
                        if result.success:
                            selector_to_cache = result.selector
                            
                            # 8. Verify if spec provided
                            verification = None
                            if step.verify:
                                verification = self._verifier.verify(step.verify)
                                
                                if not verification.success:
                                    last_error = f"Verification failed: {verification.error}"
                                    continue  # Try next retry/strategy
                            
                            # Success!
                            self._budget.record_action(success=True, was_retry=attempt > 0)
                            
                            # Cache selector
                            if selector_to_cache and self._config.use_selector_cache and cache_key:
                                self._cache.set(cache_key, selector_to_cache)
                            
                            # Capture after screenshot
                            if self._config.capture_screenshots:
                                after_state = self._verifier.capture_state()
                                screenshot_after = after_state.get("screenshot")
                            
                            step_result = StepResult(
                                step_id=step.id,
                                success=True,
                                strategy_used=strategy_used,
                                attempts=attempt + 1,
                                duration_ms=int((time.time() - start_time) * 1000),
                                verification=verification,
                                screenshot_before=screenshot_before,
                                screenshot_after=screenshot_after,
                                selector_cached=selector_to_cache,
                            )
                            
                            if self._on_step_complete:
                                self._on_step_complete(step_result)
                            
                            # W20.3: Record success for learning
                            if self._collector and app_name:
                                self._collector.ingest_execution_step(
                                    app_name=app_name,
                                    window_title=current_title,
                                    strategy=strategy_used,
                                    success=True,
                                    duration_ms=step_result.duration_ms
                                )
                            
                            return step_result
                        
                        else:
                            last_error = result.error
                            
                    except Exception as e:
                        last_error = str(e)
                        logger.exception(f"Strategy {strategy.name} failed on attempt {attempt + 1}")
            
            # All strategies failed
            self._budget.record_action(success=False)
            
            # W20.3: Record failure for learning
            if self._collector and app_name:
                self._collector.ingest_execution_step(
                    app_name=app_name,
                    window_title=current_title,
                    strategy=strategy_used or "unknown",
                    success=False,
                    duration_ms=int((time.time() - start_time) * 1000)
                )
            
            return self._make_failed_result(
                step, start_time,
                error=f"All strategies failed. Last error: {last_error}",
                strategy_used=strategy_used,
                screenshot_before=screenshot_before,
                requires_takeover=True,
                takeover_reason="All automation strategies failed",
            )
            
        except Exception as e:
            logger.exception(f"Executor error on step {step.id}")
            return self._make_failed_result(
                step, start_time,
                error=str(e),
                screenshot_before=screenshot_before,
            )

    def pause(self, reason: str) -> None:
        """Pause execution."""
        self._is_paused = True
        self._pause_reason = reason
        self._budget.pause(reason)
        logger.info(f"Executor paused: {reason}")

    def resume(self) -> None:
        """Resume execution."""
        self._is_paused = False
        self._pause_reason = ""
        self._budget.resume()
        logger.info("Executor resumed")

    def is_paused(self) -> bool:
        """Check if executor is paused."""
        return self._is_paused

    def _make_failed_result(
        self,
        step: ActionStep,
        start_time: float,
        error: str,
        strategy_used: Optional[str] = None,
        screenshot_before: Optional[str] = None,
        requires_takeover: bool = False,
        takeover_reason: Optional[str] = None,
    ) -> StepResult:
        """Create a failed StepResult."""
        result = StepResult(
            step_id=step.id,
            success=False,
            strategy_used=strategy_used,
            attempts=1,
            duration_ms=int((time.time() - start_time) * 1000),
            error=error,
            screenshot_before=screenshot_before,
        )
        
        if requires_takeover and self._on_takeover:
            self._on_takeover(takeover_reason or error)
        
        if self._on_step_complete:
            self._on_step_complete(result)
        
        return result

    def find_element(self, step: ActionStep) -> Optional[UISelector]:
        """
        Pre-find an element using available strategies.
        
        Useful for plan preview or pre-computing selectors.
        """
        for strategy in self._strategies:
            if strategy.can_handle(step):
                selector = strategy.find_element(step)
                if selector:
                    return selector
        return None

    def validate_cached_selector(self, step_id: str) -> bool:
        """Check if a cached selector is still valid."""
        selector = self._cache.get(step_id)
        if not selector:
            return False
        
        for strategy in self._strategies:
            if strategy.name == selector.strategy:
                return strategy.validate_element(selector)
        
        return False

    def get_stats(self) -> dict:
        """Get executor statistics."""
        return {
            "is_paused": self._is_paused,
            "pause_reason": self._pause_reason,
            "strategies": [s.name for s in self._strategies],
            "cache_stats": self._cache.get_stats(),
            "budget": self._budget.get_remaining(),
        }
