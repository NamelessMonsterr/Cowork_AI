"""
Flash Assistant Configuration Package.
"""

from assistant.config.paths import (
    ensure_dirs,
    get_appdata_dir,
    get_learning_db_path,
    get_logs_dir,
    get_plugins_dir,
    get_settings_path,
    get_skills_dir,
    get_sync_db_path,
)
from assistant.config.settings import AppSettings, get_settings, reload_settings
