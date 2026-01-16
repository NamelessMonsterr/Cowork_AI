"""
Base Strategy - Abstract base class for execution strategies.

Each strategy represents a different approach to executing UI actions:
- UIA: Direct UI Automation API access
- OCR: Text-based element search
- Vision: Template matching
- Coords: Direct coordinate-based control
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any

from assistant.ui_contracts.schemas import ActionStep, UISelector


@dataclass
class StrategyResult:
    """
    Result of a strategy execution attempt.
    
    Attributes:
        success: Whether the action executed successfully
        selector: The selector used/found (for caching)
        error: Error message if failed
        details: Additional strategy-specific details
    """
    success: bool
    selector: Optional[UISelector] = None
    error: Optional[str] = None
    details: dict = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class Strategy(ABC):
    """
    Abstract base class for execution strategies.
    
    Strategies are tried in priority order until one succeeds:
    1. UIA (most reliable for Windows apps)
    2. OCR (text-based search)
    3. Vision (template matching)
    4. Coords (fallback, uses raw coordinates)
    
    Each strategy must implement:
    - can_handle(): Check if this strategy can handle the action
    - execute(): Actually perform the action
    - find_element(): Find a UI element (for caching)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this strategy."""
        pass

    @property
    def priority(self) -> int:
        """
        Priority order (lower = tried first).
        Default priorities:
        - UIA: 10
        - OCR: 20
        - Vision: 30
        - Coords: 40
        """
        return 50

    @abstractmethod
    def can_handle(self, step: ActionStep) -> bool:
        """
        Check if this strategy can handle the given action step.
        
        Args:
            step: The action step to check
            
        Returns:
            True if this strategy can attempt the action
        """
        pass

    @abstractmethod
    def execute(self, step: ActionStep) -> StrategyResult:
        """
        Execute the action step.
        
        Args:
            step: The action step to execute
            
        Returns:
            StrategyResult indicating success/failure
        """
        pass

    def find_element(self, step: ActionStep) -> Optional[UISelector]:
        """
        Find the target UI element without clicking.
        
        This is used to pre-compute selectors and cache them.
        
        Args:
            step: The action step containing target info
            
        Returns:
            UISelector if found, None otherwise
        """
        return None

    def validate_element(self, selector: UISelector) -> bool:
        """
        Check if a cached selector is still valid.
        
        Args:
            selector: Previously cached selector
            
        Returns:
            True if the element still exists at the cached location
        """
        return False
