"""
W20 Verification - Learning.
"""

import sys
import os

sys.path.append(os.getcwd())
from assistant.learning.store import LearningStore
from assistant.learning.collector import LearningCollector

DB_PATH = os.path.join(os.getcwd(), "test_learn.db")


def test_learning():
    print("🧪 Testing Learning & Privacy...")

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    store = LearningStore(DB_PATH)
    collector = LearningCollector(store)

    # 1. Safe Learning
    print("Ingesting Safe Notepad Event (Success)...")
    collector.ingest_execution_step(
        "notepad.exe", "Untitled - Notepad", "UIA", True, 50
    )

    profile = store.get_app_profile("notepad.exe")
    if profile and profile["uia_success_rate"] > 0:
        print(f"✅ Learned Notepad Profile: UIA Rate={profile['uia_success_rate']:.2f}")
    else:
        print("❌ Learning Failed.")

    # 2. Sensitive Exclusion
    print("Ingesting Sensitive Bank Event...")
    collector.ingest_execution_step("chrome.exe", "My Bank Login", "Vision", True, 100)

    bank_profile = store.get_app_profile("chrome.exe")
    if not bank_profile:
        print("✅ Privacy Guard: Sensitive event IGNORED.")
    else:
        print(f"❌ Privacy LEAK: Learned from sensitive window! {bank_profile}")

    # 3. Rate Update (Failure)
    print("Ingesting Notepad Failure...")
    collector.ingest_execution_step(
        "notepad.exe", "Untitled - Notepad", "UIA", False, 500
    )

    profile_v2 = store.get_app_profile("notepad.exe")
    print(
        f"✅ Updated UIA Rate: {profile_v2['uia_success_rate']:.2f} (Should be lower)"
    )

    if profile_v2["uia_success_rate"] < profile["uia_success_rate"]:
        print("✅ Learning Curve: Rate adjusted down.")
    else:
        print("❌ Rate failed to adjust.")

    # Cleanup
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except:
            pass


if __name__ == "__main__":
    test_learning()
