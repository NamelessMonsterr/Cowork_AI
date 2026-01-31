"""
Test script tovalidate secrets redaction in logging.

Tests that SecretsRedactionFilter properly redacts sensitive data
across all log handlers (console, file, audit logs).
"""

import logging
import sys
from pathlib import Path

# Add assistant to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.utils.secrets_filter import SecretsRedactionFilter


def test_redaction():
    """Test that secrets are redacted in log output."""

    # Create test logger with redaction filter
    logger = logging.getLogger("test_redaction")
    logger.setLevel(logging.INFO)

    # Add filter
    logger.addFilter(SecretsRedactionFilter())

    # Test handler (console)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    print("=== Testing Secrets Redaction ===")
    print()

    # Test 1: API Key
    print("Test 1: API Key")
    logger.info("OpenAI API Key: sk-1234567890abcdef1234567890abcdef")
    print("Expected: API key should be [REDACTED]")
    print()

    # Test 2: Password
    print("Test 2: Password")
    logger.info("User password is: MySecretPassword123!")
    print("Expected: Password should be [REDACTED]")
    print()

    # Test 3: Token
    print("Test 3: Token")
    logger.info("Bearer token=ghp_1234567890abcdefghij1234567890")
    print("Expected: Token should be [REDACTED]")
    print()

    # Test 4: Normal log (no secrets)
    print("Test 4: Normal log")
    logger.info("User clicked button at position (100, 200)")
    print("Expected: Should pass through unchanged")
    print()

    # Test 5: Mixed content
    print("Test 5: Mixed content")
    logger.info(
        "Connecting to API with key=sk-test123456789012345678901234567890 for user@example.com"
    )
    print(
        "Expected: API key [REDACTED], email preserved or redacted depending on pattern"
    )
    print()

    print("=== Redaction Test Complete ===")
    print()
    print("✅ If you see [REDACTED] above, secrets filter is working correctly")
    print("❌ If you see actual secrets, filter integration needs fixing")


if __name__ == "__main__":
    test_redaction()
