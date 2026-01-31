"""
Custom Security Exceptions for Flash Assistant.

P0 SECURITY FIX: Added SecurityError exception class for security violations.
"""


class SecurityError(Exception):
    """Raised when a security policy is violated."""

    pass


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""

    pass
