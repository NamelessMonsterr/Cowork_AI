"""
W20.2 Feature Store.
SQLite database for storing learned optimizations and personalization.
"""

import logging
import os
import sqlite3
from typing import Any

logger = logging.getLogger("LearningStore")


class LearningStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # 1. App Profiles: Learned preferences per application
        # e.g., "notepad.exe" -> preferred_strategy="UIA", avg_latency=50ms
        c.execute("""CREATE TABLE IF NOT EXISTS app_profiles (
            app_name TEXT PRIMARY KEY,
            preferred_strategy TEXT,
            uia_success_rate REAL DEFAULT 0,
            vision_success_rate REAL DEFAULT 0,
            coords_success_rate REAL DEFAULT 0,
            sample_count INTEGER DEFAULT 0,
            last_updated REAL
        )""")

        # 2. Selector Stats: Success rates for specific UI selectors
        # e.g., "Submit Button" hash -> success=98%
        c.execute("""CREATE TABLE IF NOT EXISTS selector_stats (
            selector_hash TEXT PRIMARY KEY,
            app_name TEXT,
            selector_str TEXT,
            success_count INTEGER DEFAULT 0,
            fail_count INTEGER DEFAULT 0,
            avg_duration_ms REAL DEFAULT 0,
            last_used REAL
        )""")

        # 3. User Preferences: Learned habits
        # e.g., "default_browser" -> "chrome"
        c.execute("""CREATE TABLE IF NOT EXISTS user_prefs (
            key TEXT PRIMARY KEY,
            value TEXT,
            confidence REAL DEFAULT 0.5,
            source TEXT
        )""")

        conn.commit()
        conn.close()

    def get_app_profile(self, app_name: str) -> dict[str, Any] | None:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM app_profiles WHERE app_name = ?", (app_name,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_app_stats(self, app_name: str, strategy: str, success: bool, duration_ms: float):
        """Update success metrics for an app's strategy."""
        # Simple moving average logic would be complex in SQL,
        # for MVP we just increment counts if we had them split,
        # but here we have rates. We'll do a simple fetch-update-save.
        # Ideally this is batched or async.

        profile = self.get_app_profile(app_name)
        if not profile:
            # Init
            profile = {
                "app_name": app_name,
                "preferred_strategy": None,
                "uia_success_rate": 0.0,
                "vision_success_rate": 0.0,
                "coords_success_rate": 0.0,
                "sample_count": 0,
            }

        # Update logic (Simplified)
        # alpha = 0.1 (Learning Rate)
        alpha = 0.1
        current_rate = profile.get(f"{strategy.lower()}_success_rate", 0.0)
        new_rate = (1 - alpha) * current_rate + alpha * (1.0 if success else 0.0)

        import time

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Determine best strategy
        rates = {
            "UIA": profile["uia_success_rate"],
            "Vision": profile["vision_success_rate"],
            # "Coords": profile["coords_success_rate"] # Coords usually fallback, don't prefer
        }
        # Update the one we just used
        if strategy == "UIA":
            rates["UIA"] = new_rate
        elif strategy == "Vision":
            rates["Vision"] = new_rate

        best_strat = max(rates, key=rates.get) if rates else "UIA"

        # Upsert
        col_name = f"{strategy.lower()}_success_rate"

        # Check if row exists
        c.execute("SELECT 1 FROM app_profiles WHERE app_name = ?", (app_name,))
        if c.fetchone():
            c.execute(
                f"""UPDATE app_profiles SET
                          {col_name} = ?,
                          preferred_strategy = ?,
                          sample_count = sample_count + 1,
                          last_updated = ?
                          WHERE app_name = ?""",
                (new_rate, best_strat, time.time(), app_name),
            )
        else:
            c.execute(
                f"""INSERT INTO app_profiles
                           (app_name, {col_name}, preferred_strategy, sample_count, last_updated)
                           VALUES (?, ?, ?, 1, ?)""",
                (app_name, new_rate, best_strat, time.time()),
            )

        conn.commit()
        conn.close()
