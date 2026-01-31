"""
W20.1 Learning Collector.
Ingests execution data, ensures privacy (Redaction), and feeds the Feature Store.
"""

import logging

from assistant.learning.store import LearningStore

logger = logging.getLogger("LearningCollector")

SENSITIVE_KEYWORDS = [
    "password",
    "login",
    "sign in",
    "bank",
    "credit card",
    "otp",
    "secret",
    "private",
]


class LearningCollector:
    def __init__(self, store: LearningStore):
        self.store = store
        self.enabled = True  # Can be toggled by user

    def is_sensitive_context(self, window_title: str | None) -> bool:
        if not window_title:
            return False
        title_lower = window_title.lower()
        return any(k in title_lower for k in SENSITIVE_KEYWORDS)

    def ingest_execution_step(
        self,
        app_name: str,
        window_title: str,
        strategy: str,
        success: bool,
        duration_ms: float,
    ):
        """
        Record result of an execution step (e.g. Click, Type).
        """
        if not self.enabled:
            return

        # 1. Privacy Check
        if self.is_sensitive_context(window_title):
            # We DO NOT learn from sensitive windows to avoid polluting stats with erratic behavior
            # or capturing sensitive selector hashes.
            # However, we MIGHT want to log that "Strategy X failed on sensitive window" strictly for metrics?
            # For strict privacy (W20 mandate), we IGNORE completely.
            return

        # 2. Update Feature Store
        if app_name:
            # Normalize app name (e.g. "notepad.exe" or "Untitled - Notepad" -> "notepad")
            # Heuristic: Use process name if available, or end of title? context usually has active_app name.
            # Assuming 'app_name' passed here is clean (e.g. from GetWindowThreadProcessId logic in Computer).

            try:
                self.store.update_app_stats(app_name, strategy, success, duration_ms)
                # logger.debug(f"Learned: {app_name} Strategy({strategy}) Success={success}")
            except Exception as e:
                logger.error(f"Failed to update stats: {e}")

    def ingest_selector_stats(self, selector_hash: str, success: bool):
        # Todo: Update selector_stats table
        pass
