"""
Execution Strategies.

Export standard strategies for the executor chain.
Priority Order:
0. System (OS commands - open_app, run_shell, open_url)
1. UIA (Native Object Control)
2. Vision (Template Match / OCR)
3. Coords (Fallback)
"""

from .coords import CoordsStrategy
from .system import SystemStrategy
from .uia import UIAStrategy
from .vision import VisionStrategy

try:
    from .ocr import OCRStrategy
except ImportError:
    pass

__all__ = ["SystemStrategy", "UIAStrategy", "VisionStrategy", "CoordsStrategy"]
