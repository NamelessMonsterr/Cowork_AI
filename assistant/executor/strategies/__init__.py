"""Execution strategies for different UI automation approaches."""

from .base import Strategy, StrategyResult
from .coords import CoordsStrategy
from .uia import UIAStrategy
from .vision import VisionStrategy

__all__ = [
    "Strategy",
    "StrategyResult",
    "CoordsStrategy",
    "UIAStrategy",
    "VisionStrategy",
]

