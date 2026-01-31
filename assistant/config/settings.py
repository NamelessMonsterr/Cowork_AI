"""
P1.1 - Application Settings (Pydantic).
Single validated configuration for the entire application.
"""

import json
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger("Settings")


# Import paths after defining to avoid circular import
def _get_settings_path():
    from assistant.config.paths import get_settings_path

    return get_settings_path()


class SafetySettings(BaseModel):
    """Safety-related configuration."""

    session_ttl_minutes: int = Field(default=30, ge=1, le=120)
    require_confirmation_for_destructive: bool = True
    max_actions_per_session: int = Field(default=100, ge=10, le=1000)
    enable_kill_switch: bool = True
    kill_switch_hotkey: str = "ctrl+shift+escape"


class PluginSettings(BaseModel):
    """Plugin system configuration."""

    dev_mode: bool = False
    allow_unsigned: bool = False
    sandbox_enabled: bool = True
    host_port: int = Field(default=8766, ge=1024, le=65535)


class CloudSettings(BaseModel):
    """Cloud sync configuration."""

    enabled: bool = False
    sync_interval_minutes: int = Field(default=15, ge=5, le=60)
    sync_plugins: bool = True
    sync_skills: bool = True
    sync_settings: bool = True


class LearningSettings(BaseModel):
    """Learning system configuration."""

    enabled: bool = True
    min_samples_for_ranking: int = Field(default=5, ge=1, le=50)
    exclude_sensitive_windows: bool = True


class VoiceSettings(BaseModel):
    """Voice input configuration."""

    mode: str = Field(default="push_to_talk", pattern="^(push_to_talk|wake_word|always_on)$")
    wake_word: str = "flash"
    push_to_talk_key: str = "ctrl+space"
    # STT Engine Settings
    engine_preference: str = Field(default="auto", pattern="^(auto|faster-whisper|openai|mock)$")
    openai_api_key: str | None = None  # If set, enables OpenAI Whisper API fallback
    prefer_local_stt: bool = True  # Try local FasterWhisper first, API second
    mock_stt: bool = False  # Force mock mode (dev only)
    # Recording Settings
    mic_device: str | None = None  # Specific mic device ID, None = system default
    record_seconds: int = Field(default=5, ge=2, le=30)  # Recording duration


class ServerSettings(BaseModel):
    """Server/network configuration."""

    host: str = "127.0.0.1"  # Production: localhost only
    port: int = Field(default=8765, ge=1024, le=65535)
    cors_enabled: bool = True  # Enabled for Beta/Dev
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
    ]  # Dev only


class AppSettings(BaseModel):
    """Root application settings."""

    version: str = "1.0.0"

    # Sub-configs
    safety: SafetySettings = Field(default_factory=SafetySettings)
    plugins: PluginSettings = Field(default_factory=PluginSettings)
    cloud: CloudSettings = Field(default_factory=CloudSettings)
    learning: LearningSettings = Field(default_factory=LearningSettings)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)

    # UI preferences
    theme: str = "dark"
    show_step_details: bool = True

    @classmethod
    def load(cls) -> "AppSettings":
        """Load settings from disk or return defaults."""
        try:
            path = _get_settings_path()
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                return cls(**data)
        except Exception as e:
            logger.warning(f"Failed to load settings: {e}. Using defaults.")
        return cls()

    def save(self):
        """Persist settings to disk."""
        path = _get_settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.model_dump(), f, indent=2)
        logger.info(f"Settings saved to {path}")


# Global singleton
_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    """Get the application settings singleton."""
    global _settings
    if _settings is None:
        _settings = AppSettings.load()
    return _settings


def reload_settings():
    """Force reload settings from disk."""
    global _settings
    _settings = AppSettings.load()
    return _settings
