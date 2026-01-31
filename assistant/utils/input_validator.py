"""
Input validation and sanitization utilities for security hardening.
Prevents path traversal, command injection, and other input-based attacks.
"""

import os
import re
from typing import List, Optional
from pathlib import Path


class InputValidator:
    """Security-focused input validation and sanitization."""
    
    # Allowed application names (whitelist approach)
    ALLOWED_APPS = {
        "notepad", "calc", "calculator", "paint", "mspaint",
        "explorer", "cmd", "powershell", "chrome", "firefox",
        "edge", "msedge", "code", "vscode", "winword", "excel",
        "powerpnt", "spotify", "discord", "slack", "teams"
    }
    
    # Dangerous characters for command injection
    SHELL_METACHARACTERS = set(';&|`$(){}[]<>*?\'"\\')
    
    @staticmethod
    def validate_app_name(app_name: str) -> tuple[bool, str]:
        """
        Validate application name against whitelist.
        
        Returns:
            (is_valid, sanitized_name or error_message)
        """
        if not app_name:
            return False, "Empty application name"
        
        # Normalize
        app_lower = app_name.lower().strip()
        
        # Remove .exe suffix if present
        if app_lower.endswith('.exe'):
            app_lower = app_lower[:-4]
        
        # Check whitelist
        if app_lower not in InputValidator.ALLOWED_APPS:
            return False, f"Application '{app_name}' not in whitelist"
        
        return True, app_lower
    
    @staticmethod
    def validate_file_path(file_path: str, allowed_dirs: Optional[List[str]] = None) -> tuple[bool, str]:
        """
        Validate file path to prevent directory traversal.
        
        Args:
            file_path: Path to validate
            allowed_dirs: List of allowed base directories (optional)
            
        Returns:
            (is_valid, normalized_path or error_message)
        """
        if not file_path:
            return False, "Empty file path"
        
        try:
            # Resolve to absolute path (prevents ../ attacks)
            abs_path = os.path.abspath(os.path.realpath(file_path))
            
            # Check for null bytes (path injection)
            if '\x00' in file_path:
                return False, "Null byte in path"
            
            # If allowed directories specified, verify path is within them
            if allowed_dirs:
                is_allowed = False
                for allowed_dir in allowed_dirs:
                    allowed_abs = os.path.abspath(os.path.realpath(allowed_dir))
                    if abs_path.startswith(allowed_abs):
                        is_allowed = True
                        break
                
                if not is_allowed:
                    return False, f"Path outside allowed directories"
            
            return True, abs_path
            
        except (ValueError, OSError) as e:
            return False, f"Invalid path: {str(e)}"
    
    @staticmethod
    def sanitize_command_arg(arg: str) -> str:
        """
        Sanitize command argument by escaping shell metacharacters.
        WARNING: Prefer using subprocess with list args (shell=False) instead.
        
        Returns:
            Sanitized string
        """
        # Remove any shell metacharacters
        sanitized = ''.join(c for c in arg if c not in InputValidator.SHELL_METACHARACTERS)
        return sanitized
    
    @staticmethod
    def validate_text_input(text: str, max_length: int = 10000) -> tuple[bool, str]:
        """
        Validate text input for safe processing.
        
        Args:
            text: Text to validate
            max_length: Maximum allowed length
            
        Returns:
            (is_valid, text or error_message)
        """
        if not text:
            return False, "Empty text input"
        
        if len(text) > max_length:
            return False, f"Text exceeds maximum length ({max_length})"
        
        # Check for null bytes
        if '\x00' in text:
            return False, "Null byte in text"
        
        return True, text


def validate_session_permission_request(apps: List[str], folders: List[str]) -> tuple[bool, str]:
    """
    Validate session permission grant request.
    
    Returns:
        (is_valid, error_message)
    """
    # Reject wildcard permissions (security best practice)
    if "*" in apps or "*" in folders:
        return False, "Wildcard permissions (*) are not allowed for security reasons"
    
    # Validate each app
    for app in apps:
        is_valid, msg = InputValidator.validate_app_name(app)
        if not is_valid:
            return False, f"Invalid app: {msg}"
    
    # Validate each folder
    for folder in folders:
        is_valid, msg = InputValidator.validate_file_path(folder)
        if not is_valid:
            return False, f"Invalid folder: {msg}"
    
    return True, ""
