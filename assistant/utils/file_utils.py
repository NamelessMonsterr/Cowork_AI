"""
File reading utilities with size limits for token budget protection.
P5A FIX: Prevents token exhaustion from large file reads.
"""

import logging
import os

logger = logging.getLogger(__name__)

# P5A FIX: Configuration
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1MB limit (~250k tokens max)


def safe_read_file(file_path: str) -> str:
    """
    Reads a file if it's within safe size limits.
    Returns error message if file is too large or inaccessible.
    """
    try:
        file_size = os.path.getsize(file_path)

        if file_size > MAX_FILE_SIZE_BYTES:
            # Return LLM-friendly error message
            return (
                f"[Error] File is too large to read ({file_size:,} bytes). "
                f"Maximum allowed size is {MAX_FILE_SIZE_BYTES:,} bytes. "
                f"Please ask the user to provide a specific excerpt or handle this manually."
            )

        with open(file_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        logger.info(f"[SafeRead] Read file: {file_path} ({file_size:,} bytes)")
        return content

    except FileNotFoundError:
        return f"[Error] File not found: {file_path}"
    except PermissionError:
        return f"[Error] Permission denied: {file_path}"
    except Exception as e:
        return f"[Error] Failed to read file: {str(e)}"


def get_file_info(file_path: str) -> dict:
    """Returns safe metadata about a file without reading its contents."""
    try:
        stat = os.stat(file_path)
        return {
            "path": file_path,
            "size_bytes": stat.st_size,
            "size_readable": f"{stat.st_size / 1024:.1f} KB"
            if stat.st_size < 1024 * 1024
            else f"{stat.st_size / (1024 * 1024):.1f} MB",
            "can_read": stat.st_size <= MAX_FILE_SIZE_BYTES,
            "modified": stat.st_mtime,
        }
    except Exception as e:
        return {"error": str(e)}
