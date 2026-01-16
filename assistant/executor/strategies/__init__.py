"""
Execution Strategies.

Export standard strategies for the executor chain.
Priority Order:
1. UIA (Native Object Control)
2. Vision (Template Match / OCR)
3. Coords (Fallback)
"""

from .uia import UIAStrategy
from .vision import VisionStrategy
from .coords import CoordsStrategy
try:
    from .ocr import OCRStrategy
except ImportError:
    pass

__all__ = ["UIAStrategy", "VisionStrategy", "CoordsStrategy"]
