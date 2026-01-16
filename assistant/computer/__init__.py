"""Computer abstraction layer for Windows control."""

from .protocol import Computer
from .windows import WindowsComputer

__all__ = ["Computer", "WindowsComputer"]
