"""
Backend Entrypoint - Dedicated launcher for PyInstaller (W10.1).

Responsibility:
1. Setup paths (Frozen vs Dev).
2. Configure Logging to %APPDATA%.
3. Launch Uvicorn Server.
"""

import os
import sys

import uvicorn

# Add parent dir to path so 'assistant' package is found
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)

from assistant.main import app


def setup_frozen_env():
    """Setup environment when running as frozen EXE."""
    if getattr(sys, "frozen", False):
        # We are running in PyInstaller bundle
        # Resources are in sys._MEIPASS
        # But we write data to APPDATA
        app_data = os.path.join(os.getenv("APPDATA"), "CoworkAI")
        os.makedirs(app_data, exist_ok=True)
        os.makedirs(os.path.join(app_data, "logs"), exist_ok=True)
        os.makedirs(os.path.join(app_data, "macros"), exist_ok=True)

        # Divert stdout/stderr to log file in prod
        sys.stdout = open(os.path.join(app_data, "logs", "backend.log"), "a")
        sys.stderr = sys.stdout

        return app_data
    return None


def main():
    app_data = setup_frozen_env()

    # Port 8765 Fixed (MVP)
    # Host 127.0.0.1 (Localhost only)
    print("Starting CoworkAI Backend on 127.0.0.1:8765")

    try:
        uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
    except Exception as e:
        if app_data:
            with open(os.path.join(app_data, "logs", "crash.log"), "w") as f:
                f.write(str(e))
        raise e


if __name__ == "__main__":
    main()
