"""
UAC (User Account Control) and Secure Desktop Detection.
Handles detection of elevated privileges, secure desktops, and lock screens.
"""

import ctypes
import logging

logger = logging.getLogger("Safety.UAC")

# Windows API Constants
DESKTOP_READOBJECTS = 0x0001
DESKTOP_WRITEOBJECTS = 0x0080
UOI_NAME = 2


def is_secure_desktop() -> bool:
    """
    Check if the current desktop is a secure desktop (UAC, Lock Screen, Sign-in).

    Returns:
        True if on secure desktop (automation blocked).
    """
    user32 = ctypes.windll.user32

    try:
        # Try to open the input desktop with read rights
        hdesk = user32.OpenInputDesktop(0, False, DESKTOP_READOBJECTS)

        if hdesk == 0:
            # If we fail to open it, it's likely a secure desktop we don't have access to
            # (unless we happen to be SYSTEM, but even then)
            return True

        # Get desktop name to be sure
        name_buffer = ctypes.create_unicode_buffer(256)
        length = ctypes.c_ulong()

        result = user32.GetUserObjectInformationW(
            hdesk, UOI_NAME, name_buffer, 256 * 2, ctypes.byref(length)
        )

        user32.CloseDesktop(hdesk)

        if result:
            name = name_buffer.value.lower()
            # "winlogon" is the secure desktop used by UAC and Lock Screen
            if "winlogon" in name or "screensaver" in name:
                return True

        return False

    except Exception as e:
        logger.error(f"Error checking secure desktop: {e}")
        # Fail safe: if we can't check, assume normal unless proven otherwise?
        # Or safely assume we are blocked?
        # Usually it's better to assume False if just API error, to avoid false positives.
        return False


def is_elevated() -> bool:
    """Check if the current process has admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception as e:
        logger.debug(f"UAC elevation check failed: {e}")
        return False


def get_elevation_requirement(window_handle: int) -> bool:
    """
    Check if a window requires elevation to interact with.
    (Placeholder: requires inspecting process token)
    """
    return False
