import sys
import logging
import os

logger = logging.getLogger("PlatformCheck")


def ensure_windows_os():
    """
    Ensure the application is running on Windows.
    Can be skipped for testing via COWORK_SKIP_PLATFORM_CHECK=true.
    Raises SystemExit if not on Windows (unless skipped).
    """
    # P0-5: Allow skipping for testing
    if os.getenv("COWORK_SKIP_PLATFORM_CHECK", "").lower() == "true":
        logger.warning(
            f"⚠️ Platform check SKIPPED via COWORK_SKIP_PLATFORM_CHECK. "
            f"Detected platform: {sys.platform}. "
            "Windows-specific features may not work!"
        )
        return

    if sys.platform != "win32":
        error_msg = f"Critical Error: Flash Assistant requires Windows. Detected platform: {sys.platform}"
        logger.critical(error_msg)
        print(error_msg, file=sys.stderr)
        sys.exit(1)

    logger.info("Platform check passed: Windows detected")
