import sys
import logging

logger = logging.getLogger("PlatformCheck")

def ensure_windows_os():
    """
    Ensure the application is running on Windows.
    Raises SystemExit if not on Windows.
    """
    if sys.platform != "win32":
        error_msg = f"Critical Error: Flash Assistant requires Windows. Detected platform: {sys.platform}"
        logger.critical(error_msg)
        print(error_msg, file=sys.stderr)
        sys.exit(1)
    
    logger.info("Platform check passed: Windows detected")
