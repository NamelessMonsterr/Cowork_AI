"""
Flash Assistant Configuration Package.
"""
from assistant.config.paths import (
    get_appdata_dir,
    get_logs_dir,
    get_plugins_dir,
    get_skills_dir,
    get_learning_db_path,
    get_sync_db_path,
    get_settings_path,
    ensure_dirs
)
from assistant.config.settings import get_settings, reload_settings, AppSettings
