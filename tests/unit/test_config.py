"""
P4.1 - Config Unit Tests.
"""

import pytest


class TestPaths:
    """Tests for paths module."""

    def test_get_appdata_dir(self):
        """Test appdata directory resolution."""
        from assistant.config.paths import get_appdata_dir

        path = get_appdata_dir()
        assert path is not None
        assert "CoworkAI" in str(path) or "coworkai" in str(path).lower()

    def test_get_logs_dir_creates(self):
        """Test logs dir is created."""
        from assistant.config.paths import get_logs_dir

        path = get_logs_dir()
        assert path.exists()

    def test_all_paths_consistent(self):
        """Test all paths are under appdata."""
        from assistant.config.paths import (
            get_appdata_dir,
            get_learning_db_path,
            get_logs_dir,
            get_plugins_dir,
        )

        appdata = get_appdata_dir()
        assert str(get_logs_dir()).startswith(str(appdata))
        assert str(get_plugins_dir()).startswith(str(appdata))
        assert str(get_learning_db_path()).startswith(str(appdata))


class TestSettings:
    """Tests for settings module."""

    def test_default_settings(self):
        """Test default settings are valid."""
        from assistant.config.settings import AppSettings

        settings = AppSettings()
        assert settings.safety.session_ttl_minutes == 30
        assert settings.server.cors_enabled == False
        assert settings.learning.enabled == True

    def test_settings_validation(self):
        """Test settings validation."""
        from pydantic import ValidationError

        from assistant.config.settings import AppSettings

        # Invalid TTL should fail
        with pytest.raises(ValidationError):
            AppSettings(safety={"session_ttl_minutes": -1})

    def test_settings_serialization(self, tmp_path):
        """Test settings can be saved and loaded."""
        from assistant.config.settings import AppSettings

        settings = AppSettings()
        settings.theme = "light"

        # Serialize
        data = settings.model_dump()
        assert data["theme"] == "light"

        # Can create from dict
        loaded = AppSettings(**data)
        assert loaded.theme == "light"
