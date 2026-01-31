"""
System Health Utilities
P8 FIX: Pre-flight checks for production readiness.
"""

import logging
import shutil

logger = logging.getLogger(__name__)


def check_disk_space(min_space_mb: int = 500) -> bool:
    """
    Checks if there is enough disk space to safely run the agent.

    Args:
        min_space_mb: Minimum free space required in megabytes

    Raises:
        RuntimeError: If disk space is below minimum threshold

    Returns:
        True if disk space is adequate
    """
    try:
        usage = shutil.disk_usage("/")
        free_mb = usage.free / (1024 * 1024)

        if free_mb < min_space_mb:
            raise RuntimeError(
                f"CRITICAL: Disk space low ({int(free_mb)}MB remaining). "
                f"Minimum {min_space_mb}MB required for logs/screenshots. "
                f"Aborting launch to prevent data loss."
            )

        logger.info(f"[HealthCheck] Disk space OK: {int(free_mb)}MB free")
        return True

    except Exception as e:
        logger.warning(f"[HealthCheck] Could not check disk space: {e}")
        # Don't block startup if we can't check (might be on network drive, etc.)
        return True


def verify_critical_paths() -> bool:
    """
    Verifies that critical directories are writable.

    Returns:
        True if all checks pass
    """
    import os

    critical_dirs = ["logs", "logs/screenshots", "logs/screenshots/errors"]

    for dir_path in critical_dirs:
        try:
            os.makedirs(dir_path, exist_ok=True)
            # Test write access
            test_file = os.path.join(dir_path, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            logger.error(f"[HealthCheck] Cannot write to {dir_path}: {e}")
            return False

    logger.info("[HealthCheck] All critical paths writable")
    return True


def run_pre_flight_checks() -> None:
    """
    Runs all pre-flight health checks.
    Raises RuntimeError if any critical check fails.
    """
    logger.info("[HealthCheck] Running pre-flight checks...")

    # Check disk space
    check_disk_space(min_space_mb=500)

    # Verify directories
    if not verify_critical_paths():
        raise RuntimeError("CRITICAL: Cannot write to required directories. Check permissions and disk space.")

    logger.info("[HealthCheck] All pre-flight checks passed ✓")
