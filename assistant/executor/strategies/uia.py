"""
UIA Strategy - Native Windows UI Automation via pywinauto.

This is the most reliable strategy for Windows applications.
It uses Microsoft's UI Automation API to:
- Find elements by control type, name, automation ID
- Click buttons, type in text fields, select menu items
- Work with WinForms, WPF, UWP, Qt5, and most modern apps

Priority: 10 (highest - tried first)
"""

import time
from typing import Optional, List, Dict, Any

try:
    from pywinauto import Desktop, Application
    from pywinauto.findwindows import ElementNotFoundError, ElementAmbiguousError
    from pywinauto.controls.uiawrapper import UIAWrapper
    HAS_PYWINAUTO = True
except ImportError:
    HAS_PYWINAUTO = False

from .base import Strategy, StrategyResult
from assistant.ui_contracts.schemas import ActionStep, UISelector


class UIAStrategy(Strategy):
    """
    UI Automation strategy using pywinauto.
    
    This strategy can interact with Windows applications by understanding
    their UI structure (buttons, text fields, menus, etc.) rather than
    just clicking at coordinates.
    
    Usage:
        strategy = UIAStrategy()
        
        step = ActionStep(
            id="1",
            tool="click",
            args={
                "control_type": "Button",
                "name": "Save",
                "window_title": "Notepad"
            }
        )
        
        result = strategy.execute(step)
    """

    def __init__(self, backend: str = "uia"):
        """
        Initialize UIA Strategy.
        
        Args:
            backend: pywinauto backend - "uia" (recommended) or "win32"
        """
        self._backend = backend
        self._desktop = None
        
        if HAS_PYWINAUTO:
            self._desktop = Desktop(backend=backend)

    @property
    def name(self) -> str:
        return "uia"

    @property
    def priority(self) -> int:
        return 10  # Highest priority - try first

    def can_handle(self, step: ActionStep) -> bool:
        """
        Can handle if:
        - pywinauto is available
        - Step has UIA-compatible selector info (window_title, control_type, name, etc.)
        - Or step has a UISelector with strategy="uia"
        """
        if not HAS_PYWINAUTO:
            return False
        
        args = step.args
        
        # Check for UIA-specific arguments
        has_uia_args = any(key in args for key in [
            "window_title", "control_type", "name", "automation_id", "class_name"
        ])
        
        # Check for UIA selector
        has_uia_selector = (
            step.selector is not None and 
            step.selector.strategy == "uia"
        )
        
        # Tools that UIA can handle
        supported_tools = {"click", "double_click", "right_click", "type", "select", "focus"}
        
        return step.tool in supported_tools and (has_uia_args or has_uia_selector)

    def execute(self, step: ActionStep) -> StrategyResult:
        """Execute the action using UI Automation."""
        if not HAS_PYWINAUTO:
            return StrategyResult(
                success=False,
                error="pywinauto not installed"
            )
        
        try:
            # Find the target element
            element = self._find_element(step)
            
            if element is None:
                return StrategyResult(
                    success=False,
                    error="Element not found"
                )
            
            # Execute action based on tool type
            tool = step.tool
            
            if tool == "click":
                element.click_input()
                
            elif tool == "double_click":
                element.double_click_input()
                
            elif tool == "right_click":
                element.right_click_input()
                
            elif tool == "type":
                text = step.args.get("text", "")
                # Clear existing text first if specified
                if step.args.get("clear_first", False):
                    element.set_edit_text("")
                element.type_keys(text, with_spaces=True)
                
            elif tool == "select":
                # For combo boxes or list items
                value = step.args.get("value", "")
                element.select(value)
                
            elif tool == "focus":
                element.set_focus()
            
            else:
                return StrategyResult(
                    success=False,
                    error=f"Unsupported tool for UIA: {tool}"
                )
            
            # Build selector for caching
            rect = element.rectangle()
            selector = UISelector(
                strategy="uia",
                window_title=step.args.get("window_title"),
                control_type=step.args.get("control_type"),
                name=step.args.get("name"),
                automation_id=step.args.get("automation_id"),
                bbox=(rect.left, rect.top, rect.right, rect.bottom),
                confidence=1.0,
                last_validated_at=time.time(),
            )
            
            return StrategyResult(
                success=True,
                selector=selector,
                details={
                    "element_type": element.element_info.control_type,
                    "element_name": element.element_info.name,
                }
            )
            
        except ElementNotFoundError as e:
            return StrategyResult(
                success=False,
                error=f"Element not found: {str(e)}"
            )
        except ElementAmbiguousError as e:
            return StrategyResult(
                success=False,
                error=f"Multiple elements match criteria: {str(e)}"
            )
        except Exception as e:
            return StrategyResult(
                success=False,
                error=f"UIA execution failed: {str(e)}"
            )

    def _find_element(self, step: ActionStep) -> Optional[UIAWrapper]:
        """
        Find the target UI element.
        
        Build criteria from step args and search using pywinauto.
        """
        args = step.args
        
        # Get the target window first
        window_title = args.get("window_title")
        
        if window_title:
            # Find specific window
            try:
                windows = self._desktop.windows(title_re=f".*{window_title}.*", visible_only=True)
                if not windows:
                    return None
                window = windows[0]
            except Exception:
                return None
        else:
            # Use active/foreground window
            try:
                window = self._desktop.top_from_point(0, 0)  # Fallback
                # Actually get foreground
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                if hwnd:
                    from pywinauto import Desktop
                    window = Desktop(backend=self._backend).window(handle=hwnd)
            except Exception:
                return None
        
        # Build element criteria
        criteria = {}
        
        if "control_type" in args:
            criteria["control_type"] = args["control_type"]
        
        if "name" in args:
            criteria["title"] = args["name"]
        
        if "automation_id" in args:
            criteria["auto_id"] = args["automation_id"]
        
        if "class_name" in args:
            criteria["class_name"] = args["class_name"]
        
        if not criteria:
            return None
        
        # Search for element
        try:
            # Use child_window for recursive search
            element = window.child_window(**criteria)
            # Verify it exists
            element.wait("exists", timeout=2)
            return element.wrapper_object()
        except Exception:
            return None

    def find_element(self, step: ActionStep) -> Optional[UISelector]:
        """
        Pre-find an element and return its selector.
        
        Useful for plan preview or caching.
        """
        element = self._find_element(step)
        
        if element is None:
            return None
        
        rect = element.rectangle()
        return UISelector(
            strategy="uia",
            window_title=step.args.get("window_title"),
            control_type=step.args.get("control_type"),
            name=step.args.get("name"),
            automation_id=step.args.get("automation_id"),
            bbox=(rect.left, rect.top, rect.right, rect.bottom),
            confidence=1.0,
            last_validated_at=time.time(),
        )

    def validate_element(self, selector: UISelector) -> bool:
        """
        Check if a cached UIA selector is still valid.
        
        This verifies the element still exists at the expected location.
        """
        if selector.strategy != "uia":
            return False
        
        try:
            # Build criteria from selector
            criteria = {}
            
            if selector.control_type:
                criteria["control_type"] = selector.control_type
            
            if selector.name:
                criteria["title"] = selector.name
            
            if selector.automation_id:
                criteria["auto_id"] = selector.automation_id
            
            if not criteria:
                return False
            
            # Try to find in the expected window
            if selector.window_title:
                windows = self._desktop.windows(
                    title_re=f".*{selector.window_title}.*", 
                    visible_only=True
                )
                if not windows:
                    return False
                window = windows[0]
                
                element = window.child_window(**criteria)
                element.wait("exists", timeout=0.5)
                
                # Verify position is similar
                if selector.bbox:
                    rect = element.rectangle()
                    current_bbox = (rect.left, rect.top, rect.right, rect.bottom)
                    
                    # Allow 50px tolerance for position shifts
                    tolerance = 50
                    for i in range(4):
                        if abs(current_bbox[i] - selector.bbox[i]) > tolerance:
                            return False
                
                return True
            
            return False
            
        except Exception:
            return False

    def get_window_elements(self, window_title: str) -> List[Dict[str, Any]]:
        """
        Get all interactive elements in a window.
        
        Useful for debugging or building element maps.
        """
        if not HAS_PYWINAUTO:
            return []
        
        try:
            windows = self._desktop.windows(
                title_re=f".*{window_title}.*", 
                visible_only=True
            )
            if not windows:
                return []
            
            window = windows[0]
            elements = []
            
            # Get all descendants
            for child in window.descendants():
                try:
                    info = child.element_info
                    rect = child.rectangle()
                    elements.append({
                        "control_type": info.control_type,
                        "name": info.name,
                        "automation_id": info.automation_id,
                        "class_name": info.class_name,
                        "bbox": (rect.left, rect.top, rect.right, rect.bottom),
                    })
                except Exception:
                    continue
            
            return elements
            
        except Exception:
            return []
