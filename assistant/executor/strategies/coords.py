"""
Coords Strategy - Direct coordinate-based control via pyautogui.

This is the fallback strategy when other strategies fail.
It uses raw x,y coordinates for mouse actions and direct keyboard input.

Pros:
- Always works (doesn't need UI tree or OCR)
- Simple and fast
- Cross-application compatible

Cons:
- Fragile (coordinates may change with window resize/move)
- No semantic understanding of UI
- Can't verify element presence
"""

from typing import Optional
import time

import pyautogui

from .base import Strategy, StrategyResult
from assistant.ui_contracts.schemas import ActionStep, UISelector


# Configure pyautogui
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05  # 50ms between actions


class CoordsStrategy(Strategy):
    """
    Direct coordinate-based strategy using pyautogui.

    This strategy handles actions that specify exact coordinates.
    It's the last resort when UIA/OCR/Vision strategies fail.
    """

    @property
    def name(self) -> str:
        return "coords"

    @property
    def priority(self) -> int:
        return 40  # Last priority (fallback)

    def can_handle(self, step: ActionStep) -> bool:
        """
        Can handle if:
        - Action has explicit x,y coordinates in args
        - Action has a selector with bbox
        - Action is a keyboard-only action (no target needed)
        """
        tool = step.tool
        args = step.args

        # Keyboard-only actions always work
        if tool in ("type", "keypress", "wait"):
            return True

        # Check for explicit coordinates
        if "x" in args and "y" in args:
            return True

        # Check for selector with bbox
        if step.selector and step.selector.bbox:
            return True

        return False

    def execute(self, step: ActionStep) -> StrategyResult:
        """Execute the action using pyautogui."""
        tool = step.tool
        args = step.args.copy()

        try:
            # Get coordinates from args or selector
            x, y = self._get_coordinates(step)

            # Execute based on tool type
            if tool == "click":
                button = args.get("button", "left")
                pyautogui.click(x, y, button=button)

            elif tool == "double_click":
                pyautogui.doubleClick(x, y)

            elif tool == "right_click":
                pyautogui.rightClick(x, y)

            elif tool == "scroll":
                scroll_x = args.get("scroll_x", 0)
                scroll_y = args.get("scroll_y", 0)
                pyautogui.moveTo(x, y)
                # Convert to clicks (scroll_y: positive = up)
                clicks = scroll_y // 100 if scroll_y != 0 else 0
                if clicks != 0:
                    pyautogui.scroll(clicks)

            elif tool == "move":
                pyautogui.moveTo(x, y)

            elif tool == "drag":
                path = args.get("path", [])
                if path:
                    self._execute_drag(path)

            elif tool == "type":
                text = args.get("text", "")
                interval = args.get("interval", 0.02)
                pyautogui.typewrite(text, interval=interval)

            elif tool == "keypress":
                keys = args.get("keys", [])
                self._execute_keypress(keys)

            elif tool == "wait":
                ms = args.get("ms", 1000)
                time.sleep(ms / 1000)

            else:
                return StrategyResult(success=False, error=f"Unknown tool: {tool}")

            # Create selector for caching if we used coordinates
            selector = None
            if x is not None and y is not None:
                selector = UISelector(
                    strategy="coords",
                    bbox=(x - 5, y - 5, x + 5, y + 5),  # Small bbox around click point
                    confidence=0.5,  # Low confidence for coord-based
                )

            return StrategyResult(
                success=True,
                selector=selector,
                details={"x": x, "y": y} if x is not None else {},
            )

        except pyautogui.FailSafeException:
            return StrategyResult(
                success=False,
                error="PyAutoGUI failsafe triggered (mouse moved to corner)",
            )
        except Exception as e:
            return StrategyResult(
                success=False, error=f"Coords execution failed: {str(e)}"
            )

    def _get_coordinates(self, step: ActionStep) -> tuple[Optional[int], Optional[int]]:
        """Extract coordinates from step args or selector."""
        args = step.args

        # Explicit coordinates
        if "x" in args and "y" in args:
            return int(args["x"]), int(args["y"])

        # From selector bbox (use center)
        if step.selector and step.selector.bbox:
            center = step.selector.get_center()
            if center:
                return center

        # Keyboard actions don't need coordinates
        if step.tool in ("type", "keypress", "wait"):
            return None, None

        raise ValueError(f"No coordinates available for {step.tool}")

    def _execute_drag(self, path: list[dict]) -> None:
        """Execute a drag operation along a path."""
        if not path:
            return

        # Move to start
        start = path[0]
        pyautogui.moveTo(start.get("x", 0), start.get("y", 0))

        # Drag through path
        pyautogui.mouseDown()
        try:
            for point in path[1:]:
                pyautogui.moveTo(point.get("x", 0), point.get("y", 0), duration=0.1)
        finally:
            pyautogui.mouseUp()

    def _execute_keypress(self, keys: list[str]) -> None:
        """Execute a key combination."""
        # Map key names
        key_map = {
            "ctrl": "ctrl",
            "control": "ctrl",
            "alt": "alt",
            "shift": "shift",
            "cmd": "win",
            "win": "win",
            "super": "win",
            "enter": "enter",
            "return": "enter",
            "esc": "escape",
            "escape": "escape",
            "tab": "tab",
            "space": "space",
            "backspace": "backspace",
            "delete": "delete",
            "home": "home",
            "end": "end",
            "pageup": "pageup",
            "pagedown": "pagedown",
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right",
            "arrowup": "up",
            "arrowdown": "down",
            "arrowleft": "left",
            "arrowright": "right",
        }

        mapped = [key_map.get(k.lower(), k.lower()) for k in keys]
        pyautogui.hotkey(*mapped)

    def find_element(self, step: ActionStep) -> Optional[UISelector]:
        """
        Coords strategy can't really "find" elements.
        Returns the selector from args if available.
        """
        if "x" in step.args and "y" in step.args:
            x, y = int(step.args["x"]), int(step.args["y"])
            return UISelector(
                strategy="coords",
                bbox=(x - 5, y - 5, x + 5, y + 5),
                confidence=0.5,
            )
        return None

    def validate_element(self, selector: UISelector) -> bool:
        """
        Coords can't validate elements exist.
        We assume they're valid (hence low confidence).
        """
        return selector.strategy == "coords" and selector.bbox is not None
