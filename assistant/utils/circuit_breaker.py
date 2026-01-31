"""Circuit breaker pattern for external service calls."""

import time
import logging
from enum import Enum
from typing import Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failures detected, calls blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    
    Prevents cascading failures by stopping calls to failing services.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Raises:
           CircuitBreakerOpenError: If circuit is open (too many failures)
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker entering HALF_OPEN state")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker OPEN. Service unavailable. "
                    f"Retry after {self.recovery_timeout}s"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker CLOSED (service recovered)")
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                f"Circuit breaker OPEN after {self.failure_count} failures"
            )
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        return (
            self.last_failure_time is not None
            and time.time() - self.last_failure_time >= self.recovery_timeout
        )


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception
):
    """
    Decorator to apply circuit breaker pattern.
    
    Usage:
        @circuit_breaker(failure_threshold=3, recovery_timeout=30)
        async def call_external_api():
            ...
    """
    breaker = CircuitBreaker(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception
    )
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator
