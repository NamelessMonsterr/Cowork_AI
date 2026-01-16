"""
Verifier - Confirms actions succeeded.

After each action, verification checks that the intended effect occurred:
- Window title changed
- Text appeared on screen
- File was created
- Process started/stopped

This is critical for reliable automation - without verification,
the agent can't know if its actions actually worked.
"""

import time
import os
import subprocess
from typing import Optional, Callable
from enum import Enum

from assistant.ui_contracts.schemas import VerifySpec, VerifyType, VerificationResult


class VerificationError(Exception):
    """Raised when verification fails."""
    pass


class Verifier:
    """
    Verification engine for action outcomes.
    
    Usage:
        verifier = Verifier(computer=windows_computer)
        
        spec = VerifySpec(type="text_present", value="Download complete", timeout=5)
        result = verifier.verify(spec)
        
        if not result.success:
            print(f"Verification failed: {result.error}")
    """

    def __init__(
        self,
        computer: "WindowsComputer" = None,
        ocr_func: Optional[Callable[[bytes, tuple], str]] = None,
    ):
        """
        Initialize Verifier.
        
        Args:
            computer: WindowsComputer instance for screenshots/window info
            ocr_func: Optional OCR function (image_bytes, region) -> text
        """
        self._computer = computer
        self._ocr_func = ocr_func
        
        # Windows API for process/window checks
        import ctypes
        self._user32 = ctypes.windll.user32

    def verify(self, spec: VerifySpec) -> VerificationResult:
        """
        Perform verification according to spec.
        
        Args:
            spec: Verification specification
            
        Returns:
            VerificationResult with success/failure details
        """
        start_time = time.time()
        
        try:
            # Poll until timeout
            deadline = time.time() + spec.timeout
            last_error = None
            
            while time.time() < deadline:
                try:
                    success, actual = self._check_condition(spec)
                    
                    # Handle negation
                    if spec.negate:
                        success = not success
                    
                    if success:
                        return VerificationResult(
                            success=True,
                            verify_type=spec.type.value if isinstance(spec.type, Enum) else spec.type,
                            expected=spec.value,
                            actual=actual,
                            duration_ms=int((time.time() - start_time) * 1000),
                        )
                    
                    last_error = f"Expected: {spec.value}, Actual: {actual}"
                    
                except Exception as e:
                    last_error = str(e)
                
                # Wait before retry
                time.sleep(0.2)
            
            # Timeout
            return VerificationResult(
                success=False,
                verify_type=spec.type.value if isinstance(spec.type, Enum) else spec.type,
                expected=spec.value,
                actual=None,
                duration_ms=int((time.time() - start_time) * 1000),
                error=f"Timeout after {spec.timeout}s: {last_error}",
            )
            
        except Exception as e:
            return VerificationResult(
                success=False,
                verify_type=spec.type.value if isinstance(spec.type, Enum) else spec.type,
                expected=spec.value,
                duration_ms=int((time.time() - start_time) * 1000),
                error=str(e),
            )

    def _check_condition(self, spec: VerifySpec) -> tuple[bool, Optional[str]]:
        """
        Check a single verification condition.
        
        Returns:
            (success, actual_value)
        """
        verify_type = spec.type if isinstance(spec.type, str) else spec.type.value
        
        if verify_type == VerifyType.WINDOW_TITLE.value:
            return self._check_window_title(spec.value)
        
        elif verify_type == VerifyType.TEXT_PRESENT.value:
            return self._check_text_present(spec.value, spec.region)
        
        elif verify_type == VerifyType.TEXT_ABSENT.value:
            present, actual = self._check_text_present(spec.value, spec.region)
            return (not present, actual)
        
        elif verify_type == VerifyType.FILE_EXISTS.value:
            return self._check_file_exists(spec.value)
        
        elif verify_type == VerifyType.FILE_ABSENT.value:
            exists, actual = self._check_file_exists(spec.value)
            return (not exists, actual)
        
        elif verify_type == VerifyType.PROCESS_RUNNING.value:
            return self._check_process_running(spec.value)
        
        elif verify_type == VerifyType.PROCESS_NOT_RUNNING.value:
            running, actual = self._check_process_running(spec.value)
            return (not running, actual)
        
        elif verify_type == VerifyType.URL_CONTAINS.value:
            return self._check_url_contains(spec.value)
        
        else:
            raise ValueError(f"Unknown verification type: {verify_type}")

    def _check_window_title(self, expected: str) -> tuple[bool, Optional[str]]:
        """Check if active window title contains expected text."""
        import ctypes
        
        hwnd = self._user32.GetForegroundWindow()
        if not hwnd:
            return False, None
        
        length = self._user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        self._user32.GetWindowTextW(hwnd, buffer, length + 1)
        
        actual = buffer.value
        expected_lower = expected.lower()
        
        return expected_lower in actual.lower(), actual

    def _check_text_present(
        self, 
        expected: str, 
        region: Optional[tuple[int, int, int, int]] = None
    ) -> tuple[bool, Optional[str]]:
        """Check if text is present on screen (requires OCR)."""
        if self._ocr_func is None:
            # Without OCR, we can't verify text presence
            # Return a "can't verify" result
            return False, "[OCR not available]"
        
        if self._computer is None:
            return False, "[No computer instance]"
        
        try:
            # Get screenshot
            import base64
            screenshot_b64 = self._computer.screenshot()
            screenshot_bytes = base64.b64decode(screenshot_b64)
            
            # Run OCR
            text = self._ocr_func(screenshot_bytes, region)
            
            expected_lower = expected.lower()
            return expected_lower in text.lower(), text[:200]  # Truncate for result
            
        except Exception as e:
            return False, f"[OCR error: {e}]"

    def _check_file_exists(self, path: str) -> tuple[bool, Optional[str]]:
        """Check if a file exists."""
        # Expand environment variables and user path
        expanded = os.path.expandvars(os.path.expanduser(path))
        exists = os.path.exists(expanded)
        return exists, expanded if exists else None

    def _check_process_running(self, process_name: str) -> tuple[bool, Optional[str]]:
        """Check if a process is running."""
        try:
            # Use tasklist to check
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/NH"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            
            output = result.stdout.strip()
            is_running = process_name.lower() in output.lower()
            
            return is_running, output[:100] if is_running else None
            
        except Exception as e:
            return False, f"[Check failed: {e}]"

    def _check_url_contains(self, expected: str) -> tuple[bool, Optional[str]]:
        """
        Check if current browser URL contains expected text.
        
        Note: This requires browser integration or reading from title.
        For now, we check if the expected URL appears in the window title.
        """
        return self._check_window_title(expected)

    def capture_state(self) -> dict:
        """
        Capture current state for before/after comparison.
        
        Returns:
            Dictionary with current state info
        """
        import ctypes
        
        state = {
            "timestamp": time.time(),
        }
        
        # Active window
        hwnd = self._user32.GetForegroundWindow()
        if hwnd:
            length = self._user32.GetWindowTextLengthW(hwnd)
            buffer = ctypes.create_unicode_buffer(length + 1)
            self._user32.GetWindowTextW(hwnd, buffer, length + 1)
            state["active_window"] = {
                "hwnd": hwnd,
                "title": buffer.value,
            }
        
        # Screenshot (optional, can be expensive)
        if self._computer:
            try:
                state["screenshot"] = self._computer.screenshot()
            except Exception:
                pass
        
        return state
