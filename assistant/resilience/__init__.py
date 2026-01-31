"""
Resilience Module - Error Handling & Analytics.

Provides:
- Retry with exponential backoff
- Circuit breaker pattern
- Error classification
- Usage analytics
"""

from .errors import (
    ErrorSeverity,
    ErrorContext,
    RetryConfig,
    retry,
    CircuitState,
    CircuitBreaker,
    ErrorClassifier,
    ResilienceManager,
)

from .analytics import (
    Metric,
    MetricsCollector,
    UsageReport,
    Analytics,
    get_analytics,
)

__all__ = [
    # Errors
    "ErrorSeverity",
    "ErrorContext",
    "RetryConfig",
    "retry",
    "CircuitState",
    "CircuitBreaker",
    "ErrorClassifier",
    "ResilienceManager",
    # Analytics
    "Metric",
    "MetricsCollector",
    "UsageReport",
    "Analytics",
    "get_analytics",
]
