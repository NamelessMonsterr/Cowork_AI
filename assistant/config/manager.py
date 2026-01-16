"""
Configuration Management Module.

Provides:
- Typed configuration with defaults
- Environment variable loading
- Config file persistence
"""

import os
import json
from typing import Optional, Any, Dict
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class UIConfig:
    """UI configuration."""
    theme: str = "dark"
    font_size: int = 14
    show_debug: bool = False
    animation_speed: float = 1.0


@dataclass
class SafetyConfig:
    """Safety configuration."""
    require_approval: bool = True
    max_actions_per_task: int = 100
    max_runtime_sec: int = 300
    blocked_apps: list = field(default_factory=lambda: ["regedit", "cmd"])


@dataclass
class VoiceConfig:
    """Voice configuration."""
    enabled: bool = True
    push_to_talk_key: str = "ctrl+space"
    voice_name: str = "en-US-AriaNeural"
    speech_rate: float = 1.0


@dataclass
class PerformanceConfig:
    """Performance configuration."""
    capture_fps: int = 30
    use_dxcam: bool = True
    cache_size: int = 100


@dataclass
class AppConfig:
    """Complete application configuration."""
    ui: UIConfig = field(default_factory=UIConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # App-level
    api_port: int = 8765
    log_level: str = "INFO"
    data_dir: str = ""
    
    def __post_init__(self):
        if not self.data_dir:
            self.data_dir = os.path.join(os.path.expanduser("~"), ".cowork")


class ConfigManager:
    """
    Manages application configuration.
    
    Features:
    - Load/save config files
    - Environment variable overrides
    - Type-safe access
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self._config_path = Path(config_path) if config_path else self._default_path()
        self._config = AppConfig()
        self._load()
    
    def _default_path(self) -> Path:
        return Path.home() / ".cowork" / "config.json"
    
    @property
    def config(self) -> AppConfig:
        return self._config
    
    def _load(self):
        """Load configuration from file and environment."""
        # Load from file
        if self._config_path.exists():
            try:
                with open(self._config_path, 'r') as f:
                    data = json.load(f)
                self._apply_dict(data)
            except Exception:
                pass
        
        # Override from environment
        self._load_env()
    
    def _apply_dict(self, data: Dict[str, Any]):
        """Apply dictionary to config."""
        if "ui" in data:
            for k, v in data["ui"].items():
                if hasattr(self._config.ui, k):
                    setattr(self._config.ui, k, v)
        if "safety" in data:
            for k, v in data["safety"].items():
                if hasattr(self._config.safety, k):
                    setattr(self._config.safety, k, v)
        if "voice" in data:
            for k, v in data["voice"].items():
                if hasattr(self._config.voice, k):
                    setattr(self._config.voice, k, v)
        if "performance" in data:
            for k, v in data["performance"].items():
                if hasattr(self._config.performance, k):
                    setattr(self._config.performance, k, v)
        
        for k in ["api_port", "log_level", "data_dir"]:
            if k in data:
                setattr(self._config, k, data[k])
    
    def _load_env(self):
        """Load config from environment variables."""
        env_map = {
            "COWORK_API_PORT": ("api_port", int),
            "COWORK_LOG_LEVEL": ("log_level", str),
            "COWORK_THEME": ("ui.theme", str),
            "COWORK_VOICE_ENABLED": ("voice.enabled", lambda x: x.lower() == "true"),
        }
        
        for env_key, (config_path, converter) in env_map.items():
            value = os.environ.get(env_key)
            if value:
                try:
                    self._set_nested(config_path, converter(value))
                except:
                    pass
    
    def _set_nested(self, path: str, value: Any):
        """Set nested config value."""
        parts = path.split(".")
        obj = self._config
        for part in parts[:-1]:
            obj = getattr(obj, part)
        setattr(obj, parts[-1], value)
    
    def save(self):
        """Save configuration to file."""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "ui": asdict(self._config.ui),
            "safety": asdict(self._config.safety),
            "voice": asdict(self._config.voice),
            "performance": asdict(self._config.performance),
            "api_port": self._config.api_port,
            "log_level": self._config.log_level,
            "data_dir": self._config.data_dir,
        }
        
        with open(self._config_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot-notation key."""
        try:
            parts = key.split(".")
            obj = self._config
            for part in parts:
                obj = getattr(obj, part)
            return obj
        except:
            return default
    
    def set(self, key: str, value: Any):
        """Set config value by dot-notation key."""
        self._set_nested(key, value)
        self.save()


# Global config instance
_config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
