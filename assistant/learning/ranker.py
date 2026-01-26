"""
W20.3 Strategy Ranking Engine.
Uses learned app profiles to bias execution strategy order.
"""
import logging
from typing import List, Optional
from assistant.learning.store import LearningStore

logger = logging.getLogger("StrategyRanker")

# Default Order (Safe)
DEFAULT_ORDER = ["UIA", "Vision", "Coords"]

class StrategyRanker:
    def __init__(self, store: LearningStore):
        self.store = store
        self.enabled = True

    def get_strategy_order(self, app_name: Optional[str]) -> List[str]:
        """
        Get the optimal strategy order for a given app.
        Returns strategies sorted by learned success rate.
        """
        if not self.enabled or not app_name:
            return DEFAULT_ORDER.copy()

        profile = self.store.get_app_profile(app_name)
        if not profile or profile.get("sample_count", 0) < 5:
            # Not enough data to be confident
            return DEFAULT_ORDER.copy()

        # Build ranking
        rates = {
            "UIA": profile.get("uia_success_rate", 0.0),
            "Vision": profile.get("vision_success_rate", 0.0),
            "Coords": profile.get("coords_success_rate", 0.0)
        }

        # Sort by rate DESC
        ranked = sorted(rates.keys(), key=lambda s: rates[s], reverse=True)

        # Safety: Coords should never be first for high-risk actions
        # (We can add action_type param later for finer control)
        # For now, if Coords is first AND its rate is not significantly higher, demote it.
        if ranked[0] == "Coords":
            # Move Coords to end
            ranked.remove("Coords")
            ranked.append("Coords")

        logger.debug(f"[Ranker] {app_name}: {ranked} (UIA={rates['UIA']:.2f}, Vision={rates['Vision']:.2f})")
        return ranked
