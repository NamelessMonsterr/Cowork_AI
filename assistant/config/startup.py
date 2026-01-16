"""
P1.2 - Startup Validation.
Pre-flight checks and fail-fast error handling.
"""
import os
import sys
import socket
import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger("Startup")

@dataclass
class StartupError:
    """Explicit startup failure with hint."""
    component: str
    error: str
    hint: str
    fatal: bool = True

class StartupValidator:
    """Pre-flight checks before backend starts."""
    
    def __init__(self):
        self.errors: List[StartupError] = []
        self.warnings: List[StartupError] = []
    
    def validate_all(self) -> bool:
        """Run all validations. Returns True if startup can proceed."""
        self._check_python_version()
        self._check_appdata()
        self._check_dependencies()
        self._check_port_available()
        
        # Log results
        for err in self.errors:
            logger.critical(f"[{err.component}] {err.error} - Hint: {err.hint}")
        for warn in self.warnings:
            logger.warning(f"[{warn.component}] {warn.error} - Hint: {warn.hint}")
        
        return len(self.errors) == 0
    
    def _check_python_version(self):
        """Ensure Python 3.11+"""
        if sys.version_info < (3, 11):
            self.errors.append(StartupError(
                component="Python",
                error=f"Python {sys.version_info.major}.{sys.version_info.minor} is too old",
                hint="Install Python 3.11 or higher"
            ))
    
    def _check_appdata(self):
        """Ensure APPDATA is accessible on Windows."""
        if os.name == 'nt':
            appdata = os.environ.get('APPDATA')
            if not appdata or not os.path.isdir(appdata):
                self.errors.append(StartupError(
                    component="Environment",
                    error="APPDATA environment variable not set or invalid",
                    hint="Ensure Windows environment is properly configured"
                ))
    
    def _check_dependencies(self):
        """Check optional dependencies."""
        # DXCam (for screen capture)
        try:
            import dxcam
        except ImportError:
            self.warnings.append(StartupError(
                component="DXCam",
                error="dxcam not installed",
                hint="Install with: pip install dxcam",
                fatal=False
            ))
        
        # PyWinAuto (for UIA)
        try:
            import pywinauto
        except ImportError:
            self.errors.append(StartupError(
                component="PyWinAuto",
                error="pywinauto not installed (required for UIA strategy)",
                hint="Install with: pip install pywinauto"
            ))
        
        # OpenAI (for LLM)
        try:
            import openai
            if not os.environ.get('OPENAI_API_KEY'):
                self.warnings.append(StartupError(
                    component="OpenAI",
                    error="OPENAI_API_KEY not set",
                    hint="Set environment variable or configure in settings",
                    fatal=False
                ))
        except ImportError:
            self.errors.append(StartupError(
                component="OpenAI",
                error="openai package not installed",
                hint="Install with: pip install openai"
            ))
    
    def _check_port_available(self, port: int = 8765):
        """Check if the default port is available."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('127.0.0.1', port))
            sock.close()
        except OSError:
            self.warnings.append(StartupError(
                component="Network",
                error=f"Port {port} is already in use",
                hint="Another instance may be running, or choose a different port",
                fatal=False
            ))
    
    def get_diagnostics(self) -> dict:
        """Return diagnostic info for UI display."""
        return {
            "errors": [{"component": e.component, "error": e.error, "hint": e.hint} for e in self.errors],
            "warnings": [{"component": w.component, "error": w.error, "hint": w.hint} for w in self.warnings],
            "can_start": len(self.errors) == 0
        }
