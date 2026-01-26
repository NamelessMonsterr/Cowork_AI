"""
P4.1 - Learning Store Unit Tests.
"""
import pytest
import os


class TestLearningStore:
    """Tests for LearningStore module."""
    
    def test_create_store(self, temp_db):
        """Test store creation."""
        from assistant.learning.store import LearningStore
        
        store = LearningStore(str(temp_db))
        assert temp_db.exists()
    
    def test_update_app_profile(self, learning_store):
        """Test updating app profile."""
        learning_store.update_app_stats("notepad", "UIA", True, 100.0)
        
        profile = learning_store.get_app_profile("notepad")
        assert profile is not None
        assert profile["app_name"] == "notepad"
    
    def test_get_nonexistent_profile(self, learning_store):
        """Test getting profile for unknown app."""
        profile = learning_store.get_app_profile("unknown_app_xyz")
        assert profile is None
    
    def test_success_rate_updates(self, learning_store):
        """Test that success rate updates correctly."""
        # Add successes
        for _ in range(10):
            learning_store.update_app_stats("chrome", "Vision", True, 100.0)
        
        profile = learning_store.get_app_profile("chrome")
        assert profile["vision_success_rate"] > 0.5
    
    def test_sample_count_increments(self, learning_store):
        """Test that sample count increments."""
        learning_store.update_app_stats("app1", "UIA", True, 100.0)
        learning_store.update_app_stats("app1", "UIA", True, 100.0)
        learning_store.update_app_stats("app1", "UIA", False, 100.0)
        
        profile = learning_store.get_app_profile("app1")
        assert profile["sample_count"] == 3


class TestStrategyRanker:
    """Tests for StrategyRanker."""
    
    def test_default_order(self, learning_store):
        """Test default order for unknown apps."""
        from assistant.learning.ranker import StrategyRanker
        
        ranker = StrategyRanker(learning_store)
        order = ranker.get_strategy_order("unknown_app")
        
        assert order == ["UIA", "Vision", "Coords"]
    
    def test_learned_order(self, learning_store):
        """Test that ranker uses learned data."""
        from assistant.learning.ranker import StrategyRanker
        
        # Train: Vision works better for this app
        for _ in range(10):
            learning_store.update_app_stats("vision_app", "Vision", True, 100.0)
            learning_store.update_app_stats("vision_app", "UIA", False, 100.0)
        
        ranker = StrategyRanker(learning_store)
        order = ranker.get_strategy_order("vision_app")
        
        # Vision should be first
        assert order[0] == "Vision"
    
    def test_coords_safety(self, learning_store):
        """Test that Coords is deprioritized for safety."""
        from assistant.learning.ranker import StrategyRanker
        
        # Even if Coords has high success, it shouldn't be first
        for _ in range(10):
            learning_store.update_app_stats("coords_app", "Coords", True, 100.0)
        
        ranker = StrategyRanker(learning_store)
        order = ranker.get_strategy_order("coords_app")
        
        # Coords should not be first (safety rule)
        assert order[0] != "Coords"
