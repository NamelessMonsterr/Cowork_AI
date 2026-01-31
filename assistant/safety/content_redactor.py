"""
Content Redactor - Removes sensitive data from command output.

P1 SECURITY: Prevents accidental exposure of passwords, API keys, private keys,
credit cards, SSNs, and other PII in shell command output and logs.
"""

import logging
import re

logger = logging.getLogger(__name__)


class ContentRedactor:
    """
    Redacts sensitive information from text using regex patterns.
    
    P1 SECURITY ENHANCEMENT: Protects against data exfiltration via:
    - File reads (type, cat, Get-Content)
    - Environment variables (set, printenv)
    - Command output logging
    
    Usage:
        >>> from assistant.safety.content_redactor import ContentRedactor
        >>> output = run_command("type .env")
        >>> safe_output = ContentRedactor.redact(output)
        >>> print(safe_output)  # Passwords replaced with [PASSWORD_REDACTED]
    """

    PATTERNS = {
        # API Keys
        "api_key": r"sk-[a-zA-Z0-9]{32,}",  # OpenAI format
        "generic_api_key": r"(?:api[_-]?key|apikey)[\s]*[=:][\s]*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
        # Passwords
        "password": r"(?:password|passwd|pwd)[\s]*[=:][\s]*['\"]?([^\s'\"]+)['\"]?",
        "secret": r"(?:secret|token|auth)[\s]*[=:][\s]*['\"]?([^\s'\"]+)['\"]?",
        # Crypto Keys
        "private_key_begin": r"-----BEGIN (?:RSA|DSA|EC|OPENSSH|ENCRYPTED|PRIVATE) PRIVATE KEY-----",
        "private_key_full": r"-----BEGIN (?:RSA|DSA|EC|OPENSSH|ENCRYPTED|PRIVATE) PRIVATE KEY-----[\s\S]+?-----END (?:RSA|DSA|EC|OPENSSH|ENCRYPTED|PRIVATE) PRIVATE KEY-----",
        # Financial
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        # Connection Strings
        "connection_string": r"(?:mongodb|postgresql|mysql|redis|mssql)://[^:]+:([^@]+)@[\w\.\-:]+",
        "database_url": r"(?:DATABASE_URL|DB_URL)[\s]*[=:][\s]*['\"]?([^\s'\"]+)['\"]?",
        # Email with passwords
        "email_password": r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}):([^\s@]+)",
        # JWT Tokens
        "jwt": r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*",
        # AWS Keys
        "aws_access_key": r"AKIA[0-9A-Z]{16}",
        "aws_secret": r"(?:aws_secret_access_key|AWS_SECRET)[\s]*[=:][\s]*([a-zA-Z0-9/+=]{40})",
        # GitHub/GitLab
        "github_token": r"ghp_[a-zA-Z0-9]{36}",
        "gitlab_token": r"glpat-[a-zA-Z0-9_\-]{20,}",
        # Azure
        "azure_key": r"(?:Key|Token|Secret)[\s]*[=:][\s]*([a-zA-Z0-9+/=]{40,})",
    }

    @staticmethod
    def redact(text: str) -> tuple[str, bool]:
        """
        Redact sensitive data from text.
        
        Args:
            text: Input text potentially containing sensitive data
        
        Returns:
            Tuple of (redacted_text, was_redacted)
            - redacted_text: Text with sensitive data replaced
            - was_redacted: True if any patterns were matched
        """
        if not text:
            return text, False

        redacted = text
        was_redacted = False

        for name, pattern in ContentRedactor.PATTERNS.items():
            try:
                matches = re.findall(pattern, redacted, flags=re.IGNORECASE | re.MULTILINE)
                if matches:
                    was_redacted = True
                    redacted = re.sub(
                        pattern,
                        f"[{name.upper()}_REDACTED]",
                        redacted,
                        flags=re.IGNORECASE | re.MULTILINE,
                    )
                    logger.warning(f"🔐 Redacted {len(matches)} instance(s) of {name}")
            except re.error as e:
                logger.error(f"Invalid redaction pattern '{name}': {e}")

        if was_redacted:
            logger.info("🔐 Content redaction applied - sensitive data removed")

        return redacted, was_redacted

    @staticmethod
    def is_sensitive_file(filepath: str) -> bool:
        """
        Check if a file path indicates sensitive content.
        
        Args:
            filepath: Path to check
        
        Returns:
            True if path matches sensitive file patterns
        """
        import os

        sensitive_patterns = [
            r"\.ssh[/\\]",
            r"\.aws[/\\]",
            r"\.azure[/\\]",
            r"\.kube[/\\]config",
            r"\.env($|\.)",
            r"\.password",
            r"\.key$",
            r"\.pem$",
            r"\.pfx$",
            r"id_rsa",
            r"id_dsa",
            r"id_ecdsa",
            r"credentials",
            r"secrets",
            r"privatekey",
        ]

        path_lower = filepath.lower().replace("\\", "/")
        for pattern in sensitive_patterns:
            if re.search(pattern, path_lower, re.IGNORECASE):
                logger.critical(f"🔴 SENSITIVE FILE DETECTED: {filepath}")
                return True

        return False
