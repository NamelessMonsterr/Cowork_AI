"""
P2.3 - Database Migrations.
Schema versioning for learning.db, sync.db, etc.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from assistant.config.paths import get_appdata_dir

logger = logging.getLogger("Migrations")

SCHEMA_VERSION = 1
VERSION_FILE = "schema_version.json"


def get_version_file_path() -> Path:
    return get_appdata_dir() / VERSION_FILE


def get_current_version() -> int:
    """Get current schema version from disk."""
    path = get_version_file_path()
    if not path.exists():
        return 0

    try:
        with open(path) as f:
            data = json.load(f)
        return data.get("version", 0)
    except Exception:
        return 0


def set_version(version: int):
    """Write schema version to disk."""
    path = get_version_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump({"version": version}, f)


def run_migrations():
    """Run any pending migrations."""
    current = get_current_version()

    if current >= SCHEMA_VERSION:
        logger.info(f"Schema up to date (v{current})")
        return

    logger.info(f"Running migrations: v{current} -> v{SCHEMA_VERSION}")

    # Migration v0 -> v1: Initial schema
    if current < 1:
        _migrate_to_v1()

    # Add more migrations here as needed
    # if current < 2:
    #     _migrate_to_v2()

    set_version(SCHEMA_VERSION)
    logger.info(f"Migrations complete. Now at v{SCHEMA_VERSION}")


def _migrate_to_v1():
    """Initial schema setup."""
    logger.info("Migration v1: Initial setup")
    # Create directories
    from assistant.config.paths import ensure_dirs

    ensure_dirs()

    # Nothing else needed for fresh install


def needs_migration() -> bool:
    """Check if migrations are needed."""
    return get_current_version() < SCHEMA_VERSION
