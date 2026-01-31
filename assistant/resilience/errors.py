"""
Error Handling & Resilience Module.

Provides:
- Retry decorator with backoff
- Circuit breaker pattern
- Error classification & recovery
"""

import time
import functools
from typing import Optional, Callable, Type, Tuple, Any, Dict
from dataclasses import dataclass, field
from enum import Enum


class ErrorSeverity(str, Enum):
    """Error severity levels."""

    LOW = "low"  # Retry ok
    MEDIUM = "medium"  # Notify user
    HIGH = "high"  # Stop execution
    CRITICAL = "critical"  # Emergency stop


@dataclass
class ErrorContext:
    """Context about an error."""

    error: Exception
    severity: ErrorSeverity
    recoverable: bool
    retry_count: int
    max_retries: int
    action: Optional[str] = None
    suggestion: Optional[str] = None


class RetryConfig:
    """Retry configuration."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential: bool = True,
        jitter: bool = True,
        retry_on: Tuple[Type[Exception], ...] = (Exception,),
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential = exponential
        self.jitter = jitter
        self.retry_on = retry_on


def retry(config: Optional[RetryConfig] = None):
    """
    Retry decorator with exponential backoff.

    Usage:
        @retry(RetryConfig(max_retries=3))
        def flaky_operation():
            ...
    """
    cfg = config or RetryConfig()

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None

            for attempt in range(cfg.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except cfg.retry_on as e:
                    last_error = e

                    if attempt < cfg.max_retries:
                        delay = cfg.base_delay
                        if cfg.exponential:
                            delay *= 2**attempt
                        delay = min(delay, cfg.max_delay)

                        if cfg.jitter:
                            import random

                            delay *= 0.5 + random.random()

                        time.sleep(delay)

            raise last_error

        return wrapper

    return decorator


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for fault tolerance.

    Prevents cascading failures by stopping calls
    to failing services.
    """

    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0

    _state: CircuitState = field(default=CircuitState.CLOSED)
    _failures: int = field(default=0)
    _last_failure: float = field(default=0.0)
    _successes: int = field(default=0)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def can_execute(self) -> bool:
        return self.state != CircuitState.OPEN

    def record_success(self):
        if self._state == CircuitState.HALF_OPEN:
            self._successes += 1
            if self._successes >= 3:
                self._state = CircuitState.CLOSED
                self._failures = 0
                self._successes = 0
        else:
            self._failures = 0

    def record_failure(self):
        self._failures += 1
        self._last_failure = time.time()
        self._successes = 0

        if self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN

    def reset(self):
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._successes = 0


class ErrorClassifier:
    """Classifies errors and suggests recovery."""

    PATTERNS = {
        "timeout": (ErrorSeverity.MEDIUM, True, "Increase timeout or retry"),
        "connection": (ErrorSeverity.MEDIUM, True, "Check network, retry"),
        "permission": (ErrorSeverity.HIGH, False, "Request elevated access"),
        "not found": (ErrorSeverity.LOW, True, "Retry with different selector"),
        "out of memory": (ErrorSeverity.CRITICAL, False, "Close applications"),
    }

    @classmethod
    def classify(cls, error: Exception, action: str = "") -> ErrorContext:
        """Classify an error and return context."""
        error_str = str(error).lower()

        for pattern, (severity, recoverable, suggestion) in cls.PATTERNS.items():
            if pattern in error_str:
                return ErrorContext(
                    error=error,
                    severity=severity,
                    recoverable=recoverable,
                    retry_count=0,
                    max_retries=3 if recoverable else 0,
                    action=action,
                    suggestion=suggestion,
                )

        # Default: medium severity, recoverable
        return ErrorContext(
            error=error,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            retry_count=0,
            max_retries=3,
            action=action,
            suggestion="Retry operation",
        )


class ResilienceManager:
    """
    Manages resilience across the application.
    """

    def __init__(self):
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._error_counts: Dict[str, int] = {}

    def get_circuit(self, name: str) -> CircuitBreaker:
        if name not in self._circuits:
            self._circuits[name] = CircuitBreaker(name=name)
        return self._circuits[name]

    def record_error(self, component: str, error: Exception):
        self._error_counts[component] = self._error_counts.get(component, 0) + 1
        circuit = self.get_circuit(component)
        circuit.record_failure()

    def record_success(self, component: str):
        circuit = self.get_circuit(component)
        circuit.record_success()

    def can_execute(self, component: str) -> bool:
        return self.get_circuit(component).can_execute()

    def get_health(self) -> Dict[str, Any]:
        return {
            name: {
                "state": cb.state.value,
                "failures": cb._failures,
            }
            for name, cb in self._circuits.items()
        }
