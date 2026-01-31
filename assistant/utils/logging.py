"""
Logging Module with Privacy Sanitization.

Features:
- Structured logging
- Privacy-safe redaction of sensitive data
- File and console output
- Performance timing
"""

import logging
import os
import re
import time
from dataclasses import dataclass
from functools import wraps

# ==================== Privacy Sanitizer ====================


class PrivacySanitizer:
    """
    Sanitizes log messages to remove sensitive information.

    Patterns:
    - Email addresses
    - Phone numbers
    - Credit card numbers
    - Passwords/tokens
    - File paths (optionally)
    """

    PATTERNS = {
        "email": (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL]"),
        "phone": (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]"),
        "credit_card": (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[CARD]"),
        "ssn": (r"\b\d{3}[-]?\d{2}[-]?\d{4}\b", "[SSN]"),
        "api_key": (
            r"(api[_-]?key|token|secret)[\"']?\s*[:=]\s*[\"']?[\w-]{20,}",
            "[API_KEY]",
        ),
        "password": (
            r"(password|passwd|pwd)[\"']?\s*[:=]\s*[\"']?[^\s\"']+",
            "[PASSWORD]",
        ),
    }

    def __init__(self, redact_paths: bool = False):
        self._compiled = {
            name: (re.compile(pattern, re.IGNORECASE), replacement)
            for name, (pattern, replacement) in self.PATTERNS.items()
        }
        self._redact_paths = redact_paths

    def sanitize(self, text: str) -> str:
        """Sanitize text by replacing sensitive patterns."""
        result = text

        for name, (pattern, replacement) in self._compiled.items():
            result = pattern.sub(replacement, result)

        if self._redact_paths:
            # Replace Windows user paths
            result = re.sub(r"C:\\Users\\[^\\]+\\", r"C:\\Users\\[USER]\\", result)

        return result


# ==================== Structured Logger ====================


@dataclass
class LogConfig:
    """Logging configuration."""

    level: int = logging.INFO
    log_file: str | None = None
    console: bool = True
    sanitize: bool = True
    redact_paths: bool = True
    format_string: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


class CoworkLogger:
    """
    Structured logger with privacy sanitization.
    """

    def __init__(self, name: str = "cowork", config: LogConfig | None = None):
        self._config = config or LogConfig()
        self._sanitizer = PrivacySanitizer(redact_paths=self._config.redact_paths)

        self._logger = logging.getLogger(name)
        self._logger.setLevel(self._config.level)

        # Clear existing handlers
        self._logger.handlers.clear()

        # Formatter
        formatter = logging.Formatter(self._config.format_string)

        # Console handler
        if self._config.console:
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            self._logger.addHandler(console)

        # File handler
        if self._config.log_file:
            os.makedirs(os.path.dirname(self._config.log_file), exist_ok=True)
            file_handler = logging.FileHandler(self._config.log_file)
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

    def _sanitize(self, msg: str) -> str:
        if self._config.sanitize:
            return self._sanitizer.sanitize(msg)
        return msg

    def debug(self, msg: str, **kwargs):
        self._logger.debug(self._sanitize(msg), **kwargs)

    def info(self, msg: str, **kwargs):
        self._logger.info(self._sanitize(msg), **kwargs)

    def warning(self, msg: str, **kwargs):
        self._logger.warning(self._sanitize(msg), **kwargs)

    def error(self, msg: str, **kwargs):
        self._logger.error(self._sanitize(msg), **kwargs)

    def critical(self, msg: str, **kwargs):
        self._logger.critical(self._sanitize(msg), **kwargs)

    def action(self, action_type: str, target: str, result: str = ""):
        """Log an agent action."""
        msg = f"ACTION: {action_type} -> {target}"
        if result:
            msg += f" | {result}"
        self.info(self._sanitize(msg))

    def step(self, step_id: str, tool: str, status: str):
        """Log a step execution."""
        self.info(f"STEP[{step_id}]: {tool} - {status}")

    def timing(self, operation: str, duration_ms: float):
        """Log timing information."""
        self.debug(f"TIMING: {operation} took {duration_ms:.1f}ms")


# ==================== Performance Timer ====================


class Timer:
    """Context manager for timing operations."""

    def __init__(self, name: str, logger: CoworkLogger | None = None):
        self.name = name
        self.logger = logger
        self.start_time = 0.0
        self.elapsed_ms = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = (time.perf_counter() - self.start_time) * 1000
        if self.logger:
            self.logger.timing(self.name, self.elapsed_ms)


def timed(logger: CoworkLogger | None = None):
    """Decorator for timing function execution."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            if logger:
                logger.timing(func.__name__, elapsed)
            return result

        return wrapper

    return decorator


# ==================== Global Logger Instance ====================

_global_logger: CoworkLogger | None = None


def get_logger() -> CoworkLogger:
    """Get or create the global logger."""
    global _global_logger
    if _global_logger is None:
        _global_logger = CoworkLogger()
    return _global_logger


def configure_logging(config: LogConfig):
    """Configure the global logger."""
    global _global_logger
    _global_logger = CoworkLogger(config=config)
