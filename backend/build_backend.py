"""
Build Backend - Automates PyInstaller Build (W10.1).
"""

import os
import subprocess
import shutil


def build():
    print("🚀 Starting Backend Build...")

    # Paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend_dist = os.path.join(project_root, "backend", "dist")

    # Clean prev build
    if os.path.exists(backend_dist):
        shutil.rmtree(backend_dist)

    # PyInstaller Command
    # We use the .spec file for configuration
    cmd = ["pyinstaller", "--clean", "--noconfirm", "assistant_backend.spec"]

    print(f"Executing: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=project_root)

    # Verify Output
    exe_path = os.path.join(backend_dist, "assistant-backend.exe")
    if os.path.exists(exe_path):
        print(f"✅ Build Success: {exe_path}")
    else:
        print("❌ Build Failed: EXE not found.")
        exit(1)


if __name__ == "__main__":
    build()
