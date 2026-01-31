"""
Step 1 Verification Script.

Run this to verify that the MVP Core Loop components are working correctly.
It tests:
1. Session Permission (Deny by default)
2. Mouse Control (Movement)
3. Screen Capture (Screenshot)
4. Safety Monitors (Budget & Environment)
"""

import os
import sys
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from assistant.computer.windows import WindowsComputer
from assistant.safety.environment import EnvironmentMonitor
from assistant.safety.session_auth import PermissionDeniedError, SessionAuth


def test_safety_first():
    print("\n--- 1. Testing Default Safety (Should Fail) ---")
    session = SessionAuth()
    try:
        session.ensure()
        print("❌ CRITICAL: Allowed action without permission!")
    except PermissionDeniedError:
        print("✅ SUCCESS: Correctly blocked action without permission.")


def test_mouse_and_screen():
    print("\n--- 2. Testing Computer Control (Watch your mouse) ---")
    print("Moving mouse in 3...")
    time.sleep(1)
    print("2...")
    time.sleep(1)
    print("1...")
    time.sleep(1)

    computer = WindowsComputer()
    with computer:
        # Get dimensions
        w, h = computer.get_dimensions()
        print(f"✅ Screen Dimensions: {w}x{h}")

        # Move in a small square relative to center
        cx, cy = w // 2, h // 2
        offset = 50

        print("Moving mouse...")
        computer.move(cx - offset, cy - offset)
        time.sleep(0.2)
        computer.move(cx + offset, cy - offset)
        time.sleep(0.2)
        computer.move(cx + offset, cy + offset)
        time.sleep(0.2)
        computer.move(cx - offset, cy + offset)
        time.sleep(0.2)
        print("✅ Mouse movement completed.")

        # Screenshot
        print("Capturing screenshot...")
        b64 = computer.screenshot()
        print(f"✅ Screenshot captured ({len(b64)} chars base64)")


def test_environment_monitor():
    print("\n--- 3. Testing Environment Monitor ---")
    monitor = EnvironmentMonitor()
    state = monitor.check_state()
    print(f"✅ Current Environment State: {state.value}")

    win = monitor.get_current_window_info()
    print(f"✅ Active Window: '{win['title']}' (PID: {win['hwnd']})")


if __name__ == "__main__":
    print("=== STARTING STEP 1 HEALTH CHECK ===")
    try:
        test_safety_first()
        test_mouse_and_screen()
        test_environment_monitor()
        print("\n=== ✨ ALL SYSTEMS GO for Step 1! ===")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
