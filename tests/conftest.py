"""
P4.1 - Pytest Configuration.
Shared fixtures and test utilities.
"""

import os
import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test mode
os.environ["COWORK_TEST_MODE"] = "1"


@pytest.fixture
def temp_db(tmp_path):
    """Provide a temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture
def mock_settings():
    """Provide default settings for tests."""
    from assistant.config.settings import AppSettings

    return AppSettings()


@pytest.fixture
def learning_store(temp_db):
    """Provide a fresh learning store."""
    from assistant.learning.store import LearningStore

    return LearningStore(str(temp_db))
