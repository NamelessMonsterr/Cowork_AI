"""
Phase 2 Test: Strategy Priority/Fallback Order.

Verifies strategies are tried in correct priority order:
- UIA (priority 10) - tried first
- Vision (priority 30) - tried second  
- Coords (priority 40) - fallback
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from assistant.executor.strategies.uia import UIAStrategy
from assistant.executor.strategies.vision import VisionStrategy
from assistant.executor.strategies.coords import CoordsStrategy

def test_strategy_priority():
    print("--- Phase 2 Test: Strategy Priority ---")
    
    uia = UIAStrategy()
    vision = VisionStrategy()
    coords = CoordsStrategy()
    
    # Add in wrong order to test sorting
    strategies = [coords, vision, uia]
    sorted_strategies = sorted(strategies, key=lambda s: s.priority)
    
    print("\nStrategy priorities (lower = higher priority):")
    for s in sorted_strategies:
        print(f"  {s.name}: priority={s.priority}")
    
    # Verify order
    names = [s.name for s in sorted_strategies]
    expected = ["uia", "vision", "coords"]
    
    if names == expected:
        print("\n✅ Strategy order is correct: UIA → Vision → Coords")
        return True
    else:
        print(f"\n❌ Wrong order! Got: {names}, Expected: {expected}")
        return False

def test_strategy_availability():
    print("\n--- Phase 2 Test: Strategy Availability ---")
    
    from assistant.executor.strategies.uia import HAS_PYWINAUTO
    from assistant.executor.strategies.vision import HAS_OPENCV
    
    print(f"  pywinauto available: {'✅ Yes' if HAS_PYWINAUTO else '❌ No'}")
    print(f"  OpenCV available: {'✅ Yes' if HAS_OPENCV else '❌ No'}")
    
    return HAS_PYWINAUTO

if __name__ == "__main__":
    print("=== PHASE 2 FALLBACK TEST ===\n")
    
    priority_ok = test_strategy_priority()
    availability_ok = test_strategy_availability()
    
    if priority_ok and availability_ok:
        print("\n✨ PHASE 2 FALLBACK TEST PASSED")
        sys.exit(0)
    else:
        print("\n⚠️ Some tests failed - check output above")
        sys.exit(1)
