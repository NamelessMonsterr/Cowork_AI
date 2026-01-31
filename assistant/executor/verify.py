"""
Verifier - Confirms actions succeeded (W7.2 Tiered Verification).

Implements tiered checking:
1. UIA (Native, Fast, 1.0 confidence)
2. OCR (Visual, Slow, ~0.8 confidence)
3. Vision (Template, Slow, ~0.8 confidence)
"""

import time
import os
import subprocess
import logging
from typing import List, Dict, Any, Tuple

from assistant.ui_contracts.schemas import (
    VerifySpec,
    VerifyType,
    VerificationResult,
    UISelector,
)

# Import Strategy interface for type hinting
try:
    from assistant.executor.strategies.base import Strategy
except ImportError:
    Strategy = Any


class VerificationError(Exception):
    pass


class Verifier:
    def __init__(
        self,
        computer: "WindowsComputer" = None,
        strategies: List[Strategy] = None,
        default_confidence: float = 0.7,
    ):
        self._computer = computer
        self._strategies = strategies or []
        self._default_confidence = default_confidence

        # Build strategy lookup map
        self._strategy_map = {s.name: s for s in self._strategies}

        import ctypes

        self._user32 = ctypes.windll.user32
        self.logger = logging.getLogger("Verifier")

    def capture_state(self) -> Dict[str, Any]:
        """Capture current system state (screenshot + active window)."""
        state = {"timestamp": time.time()}

        # Capture screenshot if computer available
        if self._computer:
            try:
                # Use base64 for embedding in logs/results
                start = time.time()
                # Use screenshot_base64 for speed or take_screenshot for file?
                # Executor saves screenshot_before/after in result.
                # Let's save to file for easier debugging, or base64?
                # WindowsComputer.take_screenshot saves to file.
                path = self._computer.take_screenshot()
                if path:
                    state["screenshot"] = path
            except Exception as e:
                self.logger.warning(f"Failed to capture screenshot: {e}")

            # Capture active window
            try:
                win = self._computer.get_active_window()
                if win:
                    state["active_window"] = {
                        "title": win.title,
                        "process_id": win.process_id,
                        "rect": win.rect,
                    }
            except Exception as e:
                self.logger.warning(f"Failed to get active window: {e}")

        return state

    def verify(self, spec: VerifySpec) -> VerificationResult:
        """Perform tiered verification."""
        start_time = time.time()

        try:
            deadline = time.time() + spec.timeout
            last_error = None

            while time.time() < deadline:
                try:
                    success, details = self._check_condition_tiered(spec)

                    if spec.negate:
                        success = not success

                    if success:
                        return VerificationResult(
                            success=True,
                            verify_type=str(spec.type),
                            expected=spec.value,
                            actual=str(details),
                            duration_ms=int((time.time() - start_time) * 1000),
                        )

                    last_error = f"Expected: {spec.value}, Details: {details}"

                except Exception as e:
                    last_error = str(e)

                time.sleep(0.5)  # Polling interval

            return VerificationResult(
                success=False,
                verify_type=str(spec.type),
                expected=spec.value,
                duration_ms=int((time.time() - start_time) * 1000),
                error=f"Timeout: {last_error}",
            )

        except Exception as e:
            return VerificationResult(
                success=False,
                verify_type=str(spec.type),
                expected=spec.value,
                duration_ms=int((time.time() - start_time) * 1000),
                error=str(e),
            )

    def _check_condition_tiered(self, spec: VerifySpec) -> Tuple[bool, Any]:
        """
        Check verification condition using multiple strategies (Tiered).
        Returns: (success, details/confidence)
        """
        vtype = spec.type

        # 1. OS-Level Checks (Fastest)
        if vtype == VerifyType.PROCESS_RUNNING:
            return self._check_process(spec.value)

        if vtype == VerifyType.WINDOW_TITLE:
            return self._check_window_title(spec.value)

        if vtype == VerifyType.FILE_EXISTS:
            return self._check_file(spec.value)

        # 2. UI/Visual Checks (Tiered)
        if vtype in (VerifyType.ELEMENT_VISIBLE, VerifyType.TEXT_PRESENT):
            return self._check_visual_tiered(spec.value, vtype)

        return False, "Unknown verification type"

    def _check_visual_tiered(self, target: str, vtype: VerifyType) -> Tuple[bool, Dict]:
        """
        Try strategies in order:
        1. UIA (Exact match)
        2. Vision (Template match if target looks like template)
        3. OCR (Text match)
        """
        # Tier 1: UIA
        uia = self._strategy_map.get("uia")
        if uia:
            # Construct a dummy selector/step to query UIA
            # Trying to find element by Name
            selector = UISelector(strategy="uia", name=target)
            if uia.validate_element(selector):
                return True, {"method": "uia", "confidence": 1.0}

        # Tier 2: Vision (if target ends in .png)
        if target.lower().endswith(".png"):
            vision = self._strategy_map.get("vision")
            if vision:
                selector = UISelector(strategy="vision", template_name=target)
                if vision.validate_element(selector):
                    return True, {"method": "vision", "confidence": 0.9}

        # Tier 3: OCR (if text present check)
        # Assuming we might have an OCR strategy or vision strategy wraps OCR
        # For now, simplistic check: do we have a way to read text?
        # If 'ocr' strategy exists use it, otherwise check computer.screenshot logic
        pass

        # Fallback to legacy OCR check (slow, expensive)
        return self._check_ocr_legacy(target)

    def _check_ocr_legacy(self, text: str) -> Tuple[bool, Dict]:
        """Legacy OCR check using computer screenshot."""
        if not self._computer:
            return False, {"error": "no_computer"}

        try:
            # This assumes some OCR capability exists or computer can get text
            # Optimally, we should use a proper OCR strategy
            # For W7, we assume failure if no OCR strategy loaded
            return False, {"reason": "no_ocr_strategy"}
        except:
            return False, {}

    # --- OS Checks ---

    def _check_process(self, name: str) -> Tuple[bool, str]:
        """Check if process is running using safe subprocess call."""
        try:
            # SECURITY FIX: Use list args instead of shell=True to prevent injection
            # BEFORE: cmd = f'tasklist /FI "IMAGENAME eq {name}"', shell=True
            # AFTER: Safe list arguments
            output = subprocess.check_output(
                ["tasklist", "/FI", f"IMAGENAME eq {name}", "/NH"], text=True
            )
            return name.lower() in output.lower(), output[:50]
        except Exception as e:
            self.logger.debug(f"Process check failed for {name}: {e}")
            return False, f"Process check failed: {str(e)[:30]}"

    def _check_window_title(self, text: str) -> Tuple[bool, str]:
        hwnd = self._user32.GetForegroundWindow()
        if not hwnd:
            return False, "No active window"
        length = self._user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        self._user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value
        return text.lower() in title.lower(), title

    def _check_file(self, path: str) -> Tuple[bool, str]:
        exists = os.path.exists(os.path.expandvars(path))
        return exists, "Found" if exists else "Not found"
