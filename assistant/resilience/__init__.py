"""
Resilience Module - Error Handling & Analytics.

Provides:
- Retry with exponential backoff
- Circuit breaker pattern
- Error classification
- Usage analytics
"""

from .analytics import (
    Analytics,
    Metric,
    MetricsCollector,
    UsageReport,
    get_analytics,
)
from .errors import (
    CircuitBreaker,
    CircuitState,
    ErrorClassifier,
    ErrorContext,
    ErrorSeverity,
    ResilienceManager,
    RetryConfig,
    retry,
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
