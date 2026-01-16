"""
P1.1 - Canonical Paths Module.
Single source of truth for all file system paths.
"""
import os
from pathlib import Path
from typing import Optional

def get_appdata_dir() -> Path:
    """
    Get the application data directory.
    Windows: %APPDATA%/CoworkAI
    Linux/Mac: ~/.coworkai
    """
    if os.name == 'nt':  # Windows
        base = os.environ.get('APPDATA')
        if not base:
            # Fallback if APPDATA not set
            base = os.path.expanduser('~')
            return Path(base) / '.coworkai'
        return Path(base) / 'CoworkAI'
    else:
        # Linux/Mac
        return Path.home() / '.coworkai'

def get_logs_dir() -> Path:
    """Get logs directory."""
    path = get_appdata_dir() / 'logs'
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_plugins_dir() -> Path:
    """Get installed plugins directory."""
    path = get_appdata_dir() / 'plugins'
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_skills_dir() -> Path:
    """Get skill packs directory."""
    path = get_appdata_dir() / 'skills'
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_learning_db_path() -> Path:
    """Get learning database path."""
    return get_appdata_dir() / 'learning.db'

def get_sync_db_path() -> Path:
    """Get cloud sync database path."""
    return get_appdata_dir() / 'sync.db'

def get_macros_dir() -> Path:
    """Get recorded macros directory."""
    path = get_appdata_dir() / 'macros'
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_plugin_host_config_path() -> Path:
    """Get plugin host port config file."""
    return get_appdata_dir() / 'plugin_host.json'

def get_settings_path() -> Path:
    """Get user settings file path."""
    return get_appdata_dir() / 'settings.json'

def ensure_dirs():
    """Ensure all required directories exist."""
    get_logs_dir()
    get_plugins_dir()
    get_skills_dir()
    get_macros_dir()
