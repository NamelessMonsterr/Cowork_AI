"""
Build Scripts for Cowork AI Assistant.

Provides:
- Development server
- Production build
- Test runner
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path


# Paths
ROOT = Path(__file__).parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def run_dev():
    """Start development server."""
    print("Starting development server...")
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "assistant.main:app",
        "--host", "127.0.0.1",
        "--port", "8765",
        "--reload",
    ], cwd=ROOT)


def run_tests():
    """Run all tests."""
    print("Running tests...")
    result = subprocess.run([sys.executable, "test_all.py"], cwd=ROOT)
    return result.returncode == 0


def build_exe():
    """Build standalone executable with PyInstaller."""
    print("Building executable...")
    
    # Check pyinstaller
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Clean previous builds
    if DIST.exists():
        shutil.rmtree(DIST)
    if BUILD.exists():
        shutil.rmtree(BUILD)
    
    # Build
    result = subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "cowork.spec",
        "--clean",
    ], cwd=ROOT)
    
    if result.returncode == 0:
        print(f"\n✅ Build complete: {DIST / 'CoworkAssistant.exe'}")
    else:
        print("\n❌ Build failed")
    
    return result.returncode == 0


def clean():
    """Clean build artifacts."""
    print("Cleaning...")
    for path in [DIST, BUILD, ROOT / "__pycache__"]:
        if path.exists():
            shutil.rmtree(path)
    print("✅ Cleaned")


def check_deps():
    """Check all dependencies are installed."""
    print("Checking dependencies...")
    
    deps = {
        "fastapi": "FastAPI",
        "uvicorn": "Uvicorn",
        "pywinauto": "pywinauto",
        "mss": "mss",
        "cv2": "OpenCV",
        "keyboard": "keyboard",
        "edge_tts": "edge-tts",
    }
    
    missing = []
    for module, name in deps.items():
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name}")
            missing.append(name)
    
    if missing:
        print(f"\nMissing: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("\n✅ All dependencies installed")
    return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Cowork Build Tools")
    parser.add_argument("command", choices=["dev", "test", "build", "clean", "check"])
    
    args = parser.parse_args()
    
    commands = {
        "dev": run_dev,
        "test": run_tests,
        "build": build_exe,
        "clean": clean,
        "check": check_deps,
    }
    
    success = commands[args.command]()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
