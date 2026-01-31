"""
Context Awareness - Understanding current system state.

Provides:
- Active application tracking
- Clipboard monitoring
- System state awareness
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import ctypes
import time

try:
    import win32gui
    import win32process
    import win32clipboard

    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


@dataclass
class AppContext:
    """Current application context."""

    window_title: str
    process_name: str
    process_id: int
    is_browser: bool
    is_editor: bool
    timestamp: float


@dataclass
class ClipboardContent:
    """Clipboard content."""

    text: Optional[str]
    has_image: bool
    has_files: bool
    timestamp: float


class ContextAwareness:
    """
    Tracks and understands current system context.

    Features:
    - Active window tracking
    - Application classification
    - Clipboard monitoring
    """

    BROWSER_PROCESSES = {"chrome", "firefox", "msedge", "brave", "opera"}
    EDITOR_PROCESSES = {"notepad", "code", "sublime_text", "notepad++", "vim", "nvim"}

    def __init__(self):
        self._last_app: Optional[AppContext] = None
        self._last_clipboard: Optional[ClipboardContent] = None
        self._app_history: List[AppContext] = []

    def get_active_app(self) -> Optional[AppContext]:
        """Get current active application context."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()

            # Get window title
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value

            # Get process info
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            process_name = self._get_process_name(pid.value)

            ctx = AppContext(
                window_title=title,
                process_name=process_name,
                process_id=pid.value,
                is_browser=process_name.lower() in self.BROWSER_PROCESSES,
                is_editor=process_name.lower() in self.EDITOR_PROCESSES,
                timestamp=time.time(),
            )

            self._last_app = ctx
            self._app_history.append(ctx)
            self._app_history = self._app_history[-50:]  # Keep last 50

            return ctx

        except Exception:
            return self._last_app

    def _get_process_name(self, pid: int) -> str:
        """Get process name from PID."""
        try:
            import psutil

            proc = psutil.Process(pid)
            return proc.name().replace(".exe", "")
        except Exception:
            return "unknown"

    def get_clipboard(self) -> Optional[ClipboardContent]:
        """Get current clipboard content."""
        if not HAS_WIN32:
            return None

        try:
            win32clipboard.OpenClipboard()

            text = None
            has_image = False
            has_files = False

            # Check for text
            if win32clipboard.IsClipboardFormatAvailable(1):  # CF_TEXT
                try:
                    text = win32clipboard.GetClipboardData(13)  # CF_UNICODETEXT
                except:
                    pass

            # Check for image
            if win32clipboard.IsClipboardFormatAvailable(2):  # CF_BITMAP
                has_image = True

            # Check for files
            if win32clipboard.IsClipboardFormatAvailable(15):  # CF_HDROP
                has_files = True

            win32clipboard.CloseClipboard()

            content = ClipboardContent(
                text=text,
                has_image=has_image,
                has_files=has_files,
                timestamp=time.time(),
            )

            self._last_clipboard = content
            return content

        except Exception:
            return self._last_clipboard

    def get_recent_apps(self, limit: int = 5) -> List[AppContext]:
        """Get recently active applications."""
        seen = set()
        unique = []
        for app in reversed(self._app_history):
            if app.process_name not in seen:
                seen.add(app.process_name)
                unique.append(app)
                if len(unique) >= limit:
                    break
        return unique

    def is_in_browser(self) -> bool:
        """Check if currently in a browser."""
        app = self.get_active_app()
        return app.is_browser if app else False

    def is_in_editor(self) -> bool:
        """Check if currently in an editor."""
        app = self.get_active_app()
        return app.is_editor if app else False

    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current context."""
        app = self.get_active_app()
        clipboard = self.get_clipboard()

        return {
            "active_app": app.process_name if app else None,
            "window_title": app.window_title if app else None,
            "is_browser": app.is_browser if app else False,
            "is_editor": app.is_editor if app else False,
            "clipboard_has_text": bool(clipboard and clipboard.text),
            "clipboard_has_image": clipboard.has_image if clipboard else False,
            "recent_apps": [a.process_name for a in self.get_recent_apps()],
        }
