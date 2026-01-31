#!/usr/bin/env python3
"""
Pre-Demo Test - Verify Everything Works
Run this before recording your demo!
"""

import requests
import time

BASE = "http://127.0.0.1:8765"


def test_command(task):
    """Test a single command and report result."""
    try:
        r = requests.post(f"{BASE}/just_do_it", json={"task": task}, timeout=5)
        data = r.json()
        status = "✅" if data.get("success") else "❌"
        print(
            f"{status} {task:30} → {data.get('action', 'unknown'):15} {data.get('status', 'error')}"
        )
        return data.get("success", False)
    except Exception as e:
        print(f"❌ {task:30} → ERROR: {e}")
        return False


print("=" * 70)
print("🎬 PRE-DEMO CHECKLIST - Testing All Commands")
print("=" * 70)

# Check server
try:
    r = requests.get(f"{BASE}/health", timeout=2)
    print("✅ Server is running\n")
except:
    print("❌ Server not running! Start with: python run_backend.py\n")
    exit(1)

# Test demo commands (these will be in your video)
print("📹 DEMO COMMANDS (these are your money shots):")
print("-" * 70)

demo_commands = [
    "open notepad",
    "type Hello from voice control!",
    "screenshot",
    "wait 1",
]

all_passed = True
for cmd in demo_commands:
    if not test_command(cmd):
        all_passed = False
    time.sleep(0.5)

print()

# Test additional commands (good to know they work)
print("🔧 BONUS COMMANDS (nice to have):")
print("-" * 70)

bonus_commands = [
    "open calc",
    "volume up",
    "minimize",
]

for cmd in bonus_commands:
    test_command(cmd)
    time.sleep(0.5)

print()
print("=" * 70)

if all_passed:
    print("🎉 ALL DEMO COMMANDS PASSED! You're ready to record!")
    print()
    print("📋 RECORDING CHECKLIST:")
    print("  [ ] Open demo.html in browser")
    print("  [ ] Start screen recording (Win+Alt+R)")
    print("  [ ] Close all other apps for clean desktop")
    print("  [ ] Test mic is working")
    print("  [ ] Do 3 takes, pick the best")
    print()
    print("🎬 DEMO SCRIPT:")
    print("  1. Click voice button")
    print("  2. Say: 'open notepad'")
    print("  3. [Wait for notepad to open]")
    print("  4. Click voice button again")
    print("  5. Say: 'type Hello from voice control!'")
    print("  6. [Wait for text to appear]")
    print("  7. Click voice button")
    print("  8. Say: 'screenshot'")
    print("  9. [Show success message]")
    print()
else:
    print("⚠️  Some demo commands failed. Fix these first!")
    print("   Then run this test again before recording.")

print("=" * 70)
