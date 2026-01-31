"""
P3.3 - Diagnostics Export.
Collect logs, settings, and system info for bug reports.
"""

import os
import sys
import json
import zipfile
import platform
import logging
from datetime import datetime
from pathlib import Path

from assistant.config.paths import get_appdata_dir, get_logs_dir

logger = logging.getLogger("Diagnostics")


def get_system_info() -> dict:
    """Collect system information."""
    return {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": sys.version,
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cwd": os.getcwd(),
    }


def get_env_info() -> dict:
    """Collect relevant environment variables (sanitized)."""
    safe_keys = [
        "APPDATA",
        "USERPROFILE",
        "USERNAME",
        "COMPUTERNAME",
        "OS",
        "PROCESSOR_ARCHITECTURE",
        "NUMBER_OF_PROCESSORS",
    ]
    return {k: os.environ.get(k, "") for k in safe_keys}


def export_diagnostics(include_logs: bool = True) -> Path:
    """
    Export diagnostics as a ZIP file.
    Returns path to the ZIP.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = get_appdata_dir() / "diagnostics"
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_path = output_dir / f"flash_diagnostics_{timestamp}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. System info
        system_info = {
            "system": get_system_info(),
            "environment": get_env_info(),
            "timestamp": timestamp,
        }
        zf.writestr("system_info.json", json.dumps(system_info, indent=2))

        # 2. Settings (if exists)
        settings_path = get_appdata_dir() / "settings.json"
        if settings_path.exists():
            zf.write(settings_path, "settings.json")

        # 3. Schema version
        version_path = get_appdata_dir() / "schema_version.json"
        if version_path.exists():
            zf.write(version_path, "schema_version.json")

        # 4. Logs (last 5 files)
        if include_logs:
            logs_dir = get_logs_dir()
            if logs_dir.exists():
                log_files = sorted(
                    logs_dir.glob("*.log"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )[:5]
                for log_file in log_files:
                    zf.write(log_file, f"logs/{log_file.name}")

        # 5. Port file (for debugging)
        port_path = get_appdata_dir() / "backend.port"
        if port_path.exists():
            zf.write(port_path, "backend.port")

    logger.info(f"Diagnostics exported to: {zip_path}")
    return zip_path


def get_diagnostics_summary() -> dict:
    """Get a quick summary for display in UI."""
    appdata = get_appdata_dir()
    logs_dir = get_logs_dir()

    return {
        "appdata_path": str(appdata),
        "logs_path": str(logs_dir),
        "logs_count": len(list(logs_dir.glob("*.log"))) if logs_dir.exists() else 0,
        "settings_exists": (appdata / "settings.json").exists(),
        "learning_db_exists": (appdata / "learning.db").exists(),
        "sync_db_exists": (appdata / "sync.db").exists(),
    }
