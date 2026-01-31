"""
Vision Strategy - Template matching using OpenCV.

This strategy finds UI elements by matching template images
against the current screen. Useful for:
- Custom icons without accessible names
- Games and non-standard UIs
- Cross-platform elements

Priority: 30 (after UIA and OCR)
"""

import time
from typing import Optional

try:
    import cv2
    import numpy as np

    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

from .base import Strategy, StrategyResult
from assistant.ui_contracts.schemas import ActionStep, UISelector


class VisionStrategy(Strategy):
    """
    Vision-based strategy using OpenCV template matching.

    This strategy matches template images against the current screen
    to find UI elements. Templates are stored as small PNG images.

    Usage:
        strategy = VisionStrategy(templates_dir="./templates")

        step = ActionStep(
            id="1",
            tool="click",
            args={
                "template": "save_button.png",
                "confidence": 0.8
            }
        )

        result = strategy.execute(step)
    """

    def __init__(
        self,
        templates_dir: str = None,
        default_confidence: float = 0.8,
    ):
        """
        Initialize Vision Strategy.

        Args:
            templates_dir: Directory containing template images
            default_confidence: Minimum match confidence (0.0-1.0)
        """
        self._templates_dir = templates_dir
        self._default_confidence = default_confidence
        self._template_cache = {}

    @property
    def name(self) -> str:
        return "vision"

    @property
    def priority(self) -> int:
        return 30  # After UIA and OCR

    def can_handle(self, step: ActionStep) -> bool:
        """
        Can handle if:
        - OpenCV is available
        - Step has template argument
        - Or step has UISelector with strategy="vision"
        """
        if not HAS_OPENCV:
            return False

        args = step.args

        # Check for vision-specific arguments
        has_template = "template" in args or "template_name" in args

        # Check for vision selector
        has_vision_selector = (
            step.selector is not None and step.selector.strategy == "vision"
        )

        # Tools that vision can handle
        supported_tools = {"click", "double_click", "right_click", "wait_for"}

        return step.tool in supported_tools and (has_template or has_vision_selector)

    def execute(self, step: ActionStep) -> StrategyResult:
        """Execute the action using template matching."""
        if not HAS_OPENCV:
            return StrategyResult(success=False, error="OpenCV not installed")

        try:
            # Find the template on screen
            match = self._find_template(step)

            if match is None:
                return StrategyResult(
                    success=False, error="Template not found on screen"
                )

            x, y, confidence, bbox = match

            # Execute action based on tool type
            tool = step.tool

            import pyautogui

            if tool == "click":
                pyautogui.click(x, y)

            elif tool == "double_click":
                pyautogui.doubleClick(x, y)

            elif tool == "right_click":
                pyautogui.rightClick(x, y)

            elif tool == "wait_for":
                # Already found, just return success
                pass

            else:
                return StrategyResult(
                    success=False, error=f"Unsupported tool for vision: {tool}"
                )

            # Build selector for caching
            selector = UISelector(
                strategy="vision",
                template_name=step.args.get("template", step.args.get("template_name")),
                bbox=bbox,
                confidence=confidence,
                last_validated_at=time.time(),
            )

            return StrategyResult(
                success=True,
                selector=selector,
                details={
                    "match_x": x,
                    "match_y": y,
                    "confidence": confidence,
                },
            )

        except Exception as e:
            return StrategyResult(
                success=False, error=f"Vision execution failed: {str(e)}"
            )

    def _find_template(self, step: ActionStep):
        """
        Find template on current screen.

        Returns: (center_x, center_y, confidence, bbox) or None
        """
        import mss

        args = step.args
        template_name = args.get("template") or args.get("template_name")
        min_confidence = args.get("confidence", self._default_confidence)

        if not template_name:
            return None

        # Load template
        template = self._load_template(template_name)
        if template is None:
            return None

        # Capture screen
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor
            screenshot = sct.grab(monitor)
            screen = np.array(screenshot)
            screen = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)

        # Template matching
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val < min_confidence:
            return None

        # Get match location
        h, w = template.shape[:2]
        top_left = max_loc
        center_x = top_left[0] + w // 2
        center_y = top_left[1] + h // 2
        bbox = (top_left[0], top_left[1], top_left[0] + w, top_left[1] + h)

        return (center_x, center_y, max_val, bbox)

    def _load_template(self, template_name: str):
        """Load template image from cache or file."""
        if template_name in self._template_cache:
            return self._template_cache[template_name]

        if self._templates_dir is None:
            return None

        import os

        path = os.path.join(self._templates_dir, template_name)

        if not os.path.exists(path):
            return None

        template = cv2.imread(path)
        if template is not None:
            self._template_cache[template_name] = template

        return template

    def find_element(self, step: ActionStep) -> Optional[UISelector]:
        """Pre-find a template and return its selector."""
        match = self._find_template(step)

        if match is None:
            return None

        x, y, confidence, bbox = match

        return UISelector(
            strategy="vision",
            template_name=step.args.get("template", step.args.get("template_name")),
            bbox=bbox,
            confidence=confidence,
            last_validated_at=time.time(),
        )

    def validate_element(self, selector: UISelector) -> bool:
        """Check if template still exists at expected location."""
        if selector.strategy != "vision" or not selector.template_name:
            return False

        # Re-find template
        step = ActionStep(
            id="validate", tool="wait_for", args={"template": selector.template_name}
        )

        match = self._find_template(step)

        if match is None:
            return False

        # Check position is similar
        if selector.bbox:
            _, _, _, new_bbox = match
            tolerance = 50
            for i in range(4):
                if abs(new_bbox[i] - selector.bbox[i]) > tolerance:
                    return False

        return True
