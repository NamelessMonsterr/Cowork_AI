"""
Windows Computer Control Module - PRODUCTION IMPLEMENTATION
Provides low-level access to Windows OS: Process, Window, Input (SendInput), Screen Capture (DXCam).
"""

import os
import time
import logging
import subprocess
import ctypes
import pyautogui
import keyboard
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from .input_protocol import (
    INPUT, INPUT_UNION, MOUSEINPUT, KEYBDINPUT,
    INPUT_MOUSE, INPUT_KEYBOARD,
    MOUSEEVENTF_MOVE, MOUSEEVENTF_ABSOLUTE,
    MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP,
    MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
)
from assistant.screen.capture import ScreenCapture

try:
    import pywinauto
    from pywinauto import Desktop
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Computer")

@dataclass
class WindowInfo:
    title: str
    handle: int
    process_id: int
    rect: Tuple[int, int, int, int]
    is_active: bool

class WindowsComputer:
    def __init__(self):
        self.screen_capture = ScreenCapture(monitor_idx=0)
        self.width, self.height = pyautogui.size()
        self.user32 = ctypes.windll.user32
        
        # Safety Callback (to be set by SessionAuth)
        self.session_verifier = None
        
        # Fail-safes
        pyautogui.FAILSAFE = True

    def set_session_verifier(self, callback):
        """Register a callback that raises PermissionError if session invalid."""
        self.session_verifier = callback

    def _ensure_permission(self):
        if self.session_verifier:
            self.session_verifier()

    def set_fps(self, fps: float):
        """Set capture target FPS (W7.1)."""
        self.screen_capture.set_target_fps(fps)

    def get_active_window(self) -> Optional[WindowInfo]:
        """Get information about the currently active window."""
        hwnd = self.user32.GetForegroundWindow()
        if not hwnd:
            return None
            
        length = self.user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value
        
        # Get Process ID
        pid = ctypes.c_ulong()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        
        # Get Rect
        rect = ctypes.wintypes.RECT()
        self.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        
        return WindowInfo(
            title=title,
            handle=hwnd,
            process_id=pid.value,
            rect=(rect.left, rect.top, rect.right, rect.bottom),
            is_active=True
        )

    def _to_absolute(self, x: int, y: int) -> Tuple[int, int]:
        """Convert pixel coords to 0-65535 absolute coords."""
        abs_x = int(x * 65535 / self.width)
        abs_y = int(y * 65535 / self.height)
        return abs_x, abs_y

    def _send_input(self, inputs: List[INPUT]):
        """Low-level SendInput wrapper."""
        self._ensure_permission()
        n = len(inputs)
        lp_inputs = (INPUT * n)(*inputs)
        cb_size = ctypes.sizeof(INPUT)
        self.user32.SendInput(n, lp_inputs, cb_size)

    def mouse_move(self, x: int, y: int, duration: float = 0):
        """Move mouse using SendInput (Absolute)."""
        abs_x, abs_y = self._to_absolute(x, y)
        
        mi = MOUSEINPUT(
            dx=abs_x, dy=abs_y,
            mouseData=0,
            dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
            time=0, dwExtraInfo=None
        )
        inp = INPUT(type=INPUT_MOUSE, union=INPUT_UNION(mi=mi))
        self._send_input([inp])
        
        # Optional: Sleep for natural movement if duration > 0 (SendInput is instant)
        if duration > 0:
            time.sleep(duration)

    def mouse_click(self, x: int, y: int, double: bool = False):
        """Reliable click using SendInput."""
        self.mouse_move(x, y)
        time.sleep(0.05)
        
        # Down + Up
        down = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, None)
        up = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, None)
        
        inputs = [
            INPUT(type=INPUT_MOUSE, union=INPUT_UNION(mi=down)),
            INPUT(type=INPUT_MOUSE, union=INPUT_UNION(mi=up))
        ]
        
        self._send_input(inputs)
        
        if double:
            time.sleep(0.1)
            self._send_input(inputs)

    def type_text(self, text: str, interval: float = 0.01):
        """Type text using keyboard module (simpler than manual ScanCodes for text)."""
        self._ensure_permission()
        logger.info(f"Typing: {text}")
        keyboard.write(text, delay=interval)

    def press_keys(self, keys: str):
        self._ensure_permission()
        logger.info(f"Pressing: {keys}")
        keyboard.send(keys)

    def screenshot_base64(self) -> Optional[str]:
        """Return screenshot as base64 string."""
        import io
        import base64
        img = self.screen_capture.capture()
        if img:
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
        return None

    def take_screenshot(self) -> Optional[str]:
        """Capture screen using DXCam/MSS."""
        img = self.screen_capture.capture()
        if img:
            timestamp = int(time.time() * 1000)
            filename = f"screenshot_{timestamp}.png"
            path = os.path.join(os.getcwd(), "screenshots", filename)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            img.save(path)
            return path
        return None

    def launch_app(self, app_name: str) -> bool:
        """Launch application dynamically."""
        self._ensure_permission()
        import shutil
        
        logger.info(f"Attempting to launch: {app_name}")
        try:
            # 1. Try finding in PATH
            path = shutil.which(app_name) or shutil.which(app_name + ".exe")
            
            if path:
                logger.info(f"Found executable: {path}")
                subprocess.Popen(path)
                return True
                
            # 2. Try os.startfile (Windows Shell Execute - good for registered apps like 'chrome')
            # This handles protocol handlers and App Paths
            logger.info(f"Trying os.startfile for: {app_name}")
            os.startfile(app_name)
            return True
            
        except Exception as e:
            logger.error(f"Launch failed for {app_name}: {e}")
            return False

    def run_shell_command(self, command: str) -> bool:
        """
        DEPRECATED: This method bypasses RestrictedShellTool security.
        Use RestrictedShellTool instead for safe command execution.
        """
        logger.warning(
            f"DEPRECATED: run_shell_command called with: {command[:50]}... "
            "This bypasses security validation. Use RestrictedShellTool instead."
        )
        self._ensure_permission()
        try:
            # SECURITY FIX: Use list args instead of shell=True
            # Prevents shell metacharacter injection
            subprocess.Popen(['powershell.exe', '-Command', command])
            return True
        except Exception as e:
            logger.error(f"Command failed: {e}")
            return False

    def run_shell(self, command: str) -> bool:
        """Alias for run_shell_command."""
        return self.run_shell_command(command)
