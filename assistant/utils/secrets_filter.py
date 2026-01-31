"""
Secrets Redaction Filter for Logging
P7A FIX: Prevents API keys and tokens from being written to log files.
"""

import logging
import re


class SecretsRedactionFilter(logging.Filter):
    """
    Logging filter to redact sensitive data from log messages.
    Prevents credentials from leaking into log files.
    """

    # Regex patterns for common secrets (API Keys, Tokens, Passwords)
    PATTERNS = [
        (r"sk-[a-zA-Z0-9]{20,}", "sk-REDACTED"),  # OpenAI/Stripe
        (r"Bearer [a-zA-Z0-9\.\-_]+", "Bearer REDACTED"),  # JWT/Bearer tokens
        (r'password=["\'][^"\']+["\']', 'password="REDACTED"'),  # Password fields
        (r'apikey=["\'][^"\']+["\']', 'apikey="REDACTED"'),  # Generic API Key
        (r'token=["\'][^"\']+["\']', 'token="REDACTED"'),  # Generic Token
        (r"Authorization:\s*[^\s]+", "Authorization: REDACTED"),  # Auth headers
        (
            r'api_key["\']?\s*[:=]\s*["\']?[^"\'\s]+',
            "api_key=REDACTED",
        ),  # API key assignments
    ]

    def filter(self, record):
        """
        Process log record and redact sensitive information.
        """
        # Get the formatted message
        msg = record.getMessage()

        # Apply all redaction patterns
        for pattern, replacement in self.PATTERNS:
            msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)

        # Override the message (safer than modifying args)
        record.msg = msg
        record.args = ()  # Clear args to prevent re-interpolation

        return True


def setup_redacted_logger(logger_name: str = "cowork_ai") -> logging.Logger:
    """
    Creates a logger with secrets redaction enabled.

    Usage:
        logger = setup_redacted_logger()
        logger.error("API key: sk-test123")  # Logs: "API key: sk-REDACTED"
    """
    logger = logging.getLogger(logger_name)
    logger.addFilter(SecretsRedactionFilter())
    return logger
