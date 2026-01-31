"""
W20.3 Verification - Strategy Ranking.
"""

import os
import sys

sys.path.append(os.getcwd())
from assistant.learning.collector import LearningCollector
from assistant.learning.ranker import StrategyRanker
from assistant.learning.store import LearningStore

DB_PATH = os.path.join(os.getcwd(), "test_ranking.db")


def test_ranking():
    print("[TEST] Testing Strategy Ranking Engine (W20.3)...")

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    store = LearningStore(DB_PATH)
    collector = LearningCollector(store)
    ranker = StrategyRanker(store)

    # 1. Feed Notepad events (UIA works best)
    print("Training: Notepad loves UIA...")
    for i in range(10):
        collector.ingest_execution_step("notepad", "Untitled - Notepad", "UIA", True, 50)
    for i in range(3):
        collector.ingest_execution_step("notepad", "Untitled - Notepad", "Vision", False, 200)

    # 2. Feed Chrome events (Vision works best)
    print("Training: Chrome loves Vision...")
    for i in range(10):
        collector.ingest_execution_step("chrome", "Google - Google Chrome", "Vision", True, 100)
    for i in range(5):
        collector.ingest_execution_step("chrome", "Google - Google Chrome", "UIA", False, 300)

    # 3. Query Ranker
    notepad_order = ranker.get_strategy_order("notepad")
    chrome_order = ranker.get_strategy_order("chrome")
    unknown_order = ranker.get_strategy_order("unknown_app")

    print(f"\nNotepad Strategy Order: {notepad_order}")
    print(f"Chrome Strategy Order: {chrome_order}")
    print(f"Unknown App Order: {unknown_order}")

    # 4. Verify
    if notepad_order[0] == "UIA":
        print("[OK] Notepad correctly prefers UIA.")
    else:
        print(f"[FAIL] Notepad should prefer UIA, got {notepad_order[0]}")

    if chrome_order[0] == "Vision":
        print("[OK] Chrome correctly prefers Vision.")
    else:
        print(f"[FAIL] Chrome should prefer Vision, got {chrome_order[0]}")

    if unknown_order == ["UIA", "Vision", "Coords"]:
        print("[OK] Unknown app uses default order.")
    else:
        print(f"[WARN] Unknown app order: {unknown_order}")

    # Cleanup
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    print("\n[DONE] W20.3 Verified.")


if __name__ == "__main__":
    test_ranking()
