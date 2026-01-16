"""
Application Settings - Centralized configuration.

Uses pydantic-settings for environment variable loading.
Configuration can be overridden via .env file or environment variables.
"""

import os
from functools import lru_cache
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden via:
    - Environment variables (prefix: COWORK_)
    - .env file in project root
    """

    # ==================== General ====================
    app_name: str = "Cowork AI Assistant"
    debug: bool = False
    log_level: str = "INFO"

    # ==================== Server ====================
    server_host: str = "127.0.0.1"
    server_port: int = 8765

    # ==================== OpenAI ====================
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_org: Optional[str] = Field(default=None, alias="OPENAI_ORG")
    openai_model: str = "computer-use-preview"

    # ==================== Session ====================
    session_ttl_minutes: int = 30
    session_timeout_on_idle_minutes: int = 5

    # ==================== Safety ====================
    # Allowed applications (comma-separated)
    allowed_apps: str = "notepad,chrome,vscode,explorer,terminal,edge,firefox,code"
    
    # Allowed folders (comma-separated)
    allowed_folders: str = "Documents,Downloads,Desktop"
    
    # Blocked apps that should never be automated
    blocked_apps: str = "regedit,cmd,powershell,taskmgr,mmc,gpedit,wt"

    # ==================== Executor ====================
    max_actions_per_task: int = 50
    max_retries_per_task: int = 20
    max_runtime_seconds: int = 180
    max_consecutive_failures: int = 5
    max_plan_steps: int = 25

    # ==================== Screen Capture ====================
    capture_fps_planning: int = 5
    capture_fps_execution: int = 15
    capture_fps_idle: int = 1
    use_dxcam: bool = False  # Set True if dxcam is installed

    # ==================== Voice ====================
    voice_enabled: bool = True
    whisper_model: str = "large-v3-turbo"
    whisper_device: str = "auto"  # "cpu", "cuda", or "auto"
    tts_voice: str = "en-US-AriaNeural"
    tts_rate: str = "+0%"

    # ==================== Logging ====================
    log_actions: bool = True
    log_screenshots: bool = True
    log_retention_days: int = 7
    log_directory: str = "logs"

    # ==================== Cache ====================
    selector_cache_size: int = 100
    selector_cache_ttl_seconds: int = 300

    # ==================== Kill Switch ====================
    kill_switch_hotkey: str = "ctrl+shift+q"

    class Config:
        env_prefix = "COWORK_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def get_allowed_apps_list(self) -> List[str]:
        """Get allowed apps as list."""
        return [app.strip().lower() for app in self.allowed_apps.split(",") if app.strip()]

    def get_allowed_folders_list(self) -> List[str]:
        """Get allowed folders as list."""
        return [folder.strip() for folder in self.allowed_folders.split(",") if folder.strip()]

    def get_blocked_apps_list(self) -> List[str]:
        """Get blocked apps as list."""
        return [app.strip().lower() for app in self.blocked_apps.split(",") if app.strip()]


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to avoid re-reading env vars on every call.
    """
    return Settings()


# Default permissions config (exported as JSON-compatible dict)
DEFAULT_PERMISSIONS = {
    "allowed_apps": [
        "notepad",
        "chrome",
        "edge",
        "firefox",
        "vscode",
        "code",
        "explorer",
        "terminal",
        "calculator",
        "paint",
    ],
    "blocked_apps": [
        "regedit",
        "cmd",
        "powershell",
        "wt",
        "taskmgr",
        "mmc",
        "gpedit",
        "secpol",
    ],
    "allowed_folders": [
        "Documents",
        "Downloads",
        "Desktop",
        "Pictures",
        "Videos",
        "Music",
    ],
    "blocked_folders": [
        "Windows",
        "Program Files",
        "Program Files (x86)",
        "System32",
        "AppData",
    ],
    "blocked_domains": [
        "*.exe",
        "registry",
        "admin",
    ],
    "sensitive_patterns": [
        "password",
        "sign in",
        "login",
        "captcha",
        "otp",
        "verification",
        "2fa",
        "two-factor",
        "user account control",
        "windows security",
    ],
}
