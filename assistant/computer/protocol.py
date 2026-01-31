"""Computer protocol definition for Windows control."""

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass
class WindowInfo:
    """Information about a window."""

    hwnd: int
    title: str
    class_name: str
    rect: tuple[int, int, int, int]  # left, top, right, bottom
    is_visible: bool
    is_minimized: bool
    process_id: int
    process_name: str


class Computer(Protocol):
    """
    Protocol defining the interface for computer control.

    All implementations must provide these methods for the agent to interact
    with the computer environment.
    """

    def get_environment(self) -> Literal["windows", "mac", "linux", "browser"]:
        """Return the environment type."""
        ...

    def get_dimensions(self) -> tuple[int, int]:
        """Return screen dimensions (width, height)."""
        ...

    def screenshot(self) -> str:
        """Capture screenshot and return as base64 encoded string."""
        ...

    # Mouse actions
    def click(self, x: int, y: int, button: str = "left") -> None:
        """Click at coordinates."""
        ...

    def double_click(self, x: int, y: int) -> None:
        """Double click at coordinates."""
        ...

    def right_click(self, x: int, y: int) -> None:
        """Right click at coordinates."""
        ...

    def scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> None:
        """Scroll at position."""
        ...

    def move(self, x: int, y: int) -> None:
        """Move mouse to coordinates."""
        ...

    def drag(self, path: list[dict[str, int]]) -> None:
        """Drag along a path of points."""
        ...

    # Keyboard actions
    def type(self, text: str) -> None:
        """Type text."""
        ...

    def keypress(self, keys: list[str]) -> None:
        """Press key combination."""
        ...

    # Utility
    def wait(self, ms: int = 1000) -> None:
        """Wait for specified milliseconds."""
        ...

    # Windows-specific (optional for other platforms)
    def get_active_window(self) -> WindowInfo | None:
        """Get information about the currently active window."""
        ...

    def get_window_by_title(self, title: str) -> WindowInfo | None:
        """Find window by title (partial match)."""
        ...

    def focus_window(self, hwnd: int) -> None:
        """Bring window to foreground."""
        ...

    def open_app(self, app_name: str) -> None:
        """Open an application by name."""
        ...
