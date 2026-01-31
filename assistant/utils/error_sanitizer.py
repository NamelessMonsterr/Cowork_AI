"""
Error Sanitization Utilities
HIGH SECURITY: Prevents leaking server details to frontend
"""

import logging
import traceback
from typing import Any

logger = logging.getLogger(__name__)


def sanitize_error_for_client(error: Exception, include_type: bool = False) -> dict[str, Any]:
    """
    Sanitize error for client response.
    
    HIGH SECURITY FIX: Prevents stack traces and internal details from leaking
    
    Args:
        error: The exception to sanitize
        include_type: Whether to include the exception type name
        
    Returns:
        Sanitized error dictionary safe for client
    """
    # Log full error server-side
    logger.error(f"Error occurred: {error}", exc_info=True)
    
    # Generic messages for different error types
    safe_messages = {
        "FileNotFoundError": "The requested resource was not found",
        "PermissionError": "Access denied",
        "ValueError": "Invalid input provided",
        "TimeoutError": "The operation timed out",
        "ConnectionError": "Unable to connect to the service",
    }
    
    error_type = type(error).__name__
    
    # Use safe message if available, otherwise generic
    message = safe_messages.get(error_type, "An internal error occurred")
    
    result = {"detail": message}
    
    if include_type:
        result["error_type"] = error_type
    
    return result


def safe_http_exception_detail(detail: str, max_length: int = 200) -> str:
    """
    Sanitize HTTPException detail for client.
    
    Truncates long details and removes file paths.
    
    Args:
        detail: The detail string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized detail string
    """
    # Remove file paths (common in tracebacks)
    import re
    detail = re.sub(r'[A-Z]:\\[^\s]+', '<file path>', detail)
    detail = re.sub(r'/[^\s]+\.py', '<file path>', detail)
    
    # Truncate if too long
    if len(detail) > max_length:
        detail = detail[:max_length] + "..."
    
    return detail
