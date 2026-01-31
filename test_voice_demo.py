#!/usr/bin/env python3
"""
Quick demo test for voice-controlled computer.
Usage: python test_voice_demo.py
"""

import requests
import sys
import time

BASE = "http://127.0.0.1:8765"


def test_direct_commands():
    """Test direct text commands."""
    print("=" * 60)
    print("TESTING DIRECT COMMANDS")
    print("=" * 60)

    test_cases = [
        {"task": "open notepad", "expected_success": True},
        {"task": "type hello world", "expected_success": True},
        {"task": "screenshot", "expected_success": True},
        {"task": "wait 2", "expected_success": True},
    ]

    for test in test_cases:
        print(f"\n🎯 Testing: '{test['task']}'")
        try:
            r = requests.post(
                f"{BASE}/just_do_it", json={"task": test["task"]}, timeout=10
            )
            data = r.json()

            if data.get("success") == test["expected_success"]:
                print(f"   ✅ PASS: {data.get('action', 'unknown')}")
            else:
                print(f"   ❌ FAIL: {data}")

        except Exception as e:
            print(f"   💥 ERROR: {e}")


def test_voice_execute():
    """Test voice execution (requires speaking)."""
    print("\n" + "=" * 60)
    print("TESTING VOICE EXECUTION")
    print("=" * 60)
    print("You will have 5 seconds to speak after each prompt")
    print("Say something like: 'open calculator' or 'type hello'")
    print("=" * 60)

    input("Press ENTER when ready to start (or Ctrl+C to skip)...")

    for i in range(3):
        print(f"\n🎤 Recording {i + 1}/3...")
        try:
            r = requests.post(f"{BASE}/voice/execute?seconds=5", timeout=15)
            data = r.json()

            if data.get("success"):
                print("   ✅ SUCCESS!")
                print(f"   Heard: '{data.get('transcript')}'")
                print(
                    f"   Action: {data.get('execution', {}).get('action', 'unknown')}"
                )
            else:
                print(
                    f"   ❌ FAILED: {data.get('error') or data.get('transcript', 'no speech')}"
                )

            time.sleep(1)

        except KeyboardInterrupt:
            print("\nSkipping...")
            break
        except Exception as e:
            print(f"   💥 ERROR: {e}")


if __name__ == "__main__":
    print("CoworkAI Voice Demo Test")
    print(f"Connecting to: {BASE}")

    # Check server
    try:
        r = requests.get(f"{BASE}/health", timeout=2)
        print("✅ Server is up!")
    except:
        print(f"❌ Server not responding at {BASE}")
        print("Start it with: python run_backend.py")
        sys.exit(1)

    # Run tests
    test_direct_commands()

    try:
        test_voice_execute()
    except KeyboardInterrupt:
        print("\n\nStopped by user.")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)
