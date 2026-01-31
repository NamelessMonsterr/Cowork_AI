"""
W15 Verification - Telemetry.
"""

import sys
import os

sys.path.append(os.getcwd())

from assistant.telemetry.client import TelemetryClient


def test_telemetry():
    print("🧪 Testing Telemetry...")
    client = TelemetryClient()

    # 1. Default should be disabled
    if client.enabled:
        print("❌ Should be disabled by default")

    # 2. Track (should ignore)
    client.track("test_ignored")
    if client.buffer:
        print("❌ Buffer should be empty")

    # 3. Enable
    print("Enabling telemetry...")
    client.enable()

    # 4. Track
    client.track("task_started", {"user_id": 123})
    client.track("step_completed", {"tool": "click"})

    # 5. Sanitize Check
    client.track("input_logged", {"password": "secret_value", "safe": "value"})
    last_event = client.buffer[-1]
    if "password" in last_event["properties"]:
        print("❌ PII Not Sanitized!")
    else:
        print("✅ PII Sanitized.")

    # 6. Flush
    print(f"Buffer size: {len(client.buffer)}")
    client.flush()
    if client.buffer:
        print("❌ Flush failed")
    else:
        print("✅ Flush success")


if __name__ == "__main__":
    test_telemetry()
