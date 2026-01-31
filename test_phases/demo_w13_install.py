"""
W13 Verification - Plugin Installer Demo.
"""

import sys
import os

sys.path.append(os.getcwd())

import json
import zipfile
import io
import logging
from assistant.plugins.installer import PluginInstaller

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("W13_Demo")


def create_dummy_plugin_zip(id="demo.plugin", publisher="LocalDev") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        manifest = {
            "id": id,
            "name": "Demo Plugin",
            "version": "1.0",
            "publisher": publisher,
            "description": "Test Plugin",
            "entrypoint": "demo:DemoPlugin",
            "permissions_required": [],
            "tools": [],
        }
        zf.writestr("plugin.json", json.dumps(manifest))
        zf.writestr("demo.py", "# code")

    return buffer.getvalue()


def test_install():
    logger.info("--- W13 Installer Verification ---")
    installer = PluginInstaller()

    # 1. Test Valid Install
    logger.info("Test 1: Valid Install")
    zip_bytes_valid = create_dummy_plugin_zip()
    try:
        pid, status = installer.install_zip(zip_bytes_valid)
        if pid == "demo.plugin" and status == "success":
            logger.info("✅ Valid install succeeded.")
        else:
            logger.error(f"❌ Valid install unexpected result: {pid} {status}")
    except Exception as e:
        logger.error(f"❌ Valid install failed: {e}")

    # 2. Test Path Traversal
    logger.info("Test 2: Path Traversal Security")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("../evil.txt", "attack")
        zf.writestr("plugin.json", "{}")

    try:
        installer.install_zip(buffer.getvalue())
        logger.error("❌ Failed to block path traversal.")
    except ValueError as e:
        if "Security Violation" in str(e):
            logger.info("✅ Path traversal blocked correctly.")
        else:
            logger.warning(f"Blocked with different error: {e}")

    # 3. Test Untrusted Publisher (Should warn but install in MVP)
    logger.info("Test 3: Untrusted Publisher")
    zip_bytes_untrusted = create_dummy_plugin_zip(
        id="evil.plugin", publisher="EvilCorp"
    )
    try:
        pid, status = installer.install_zip(zip_bytes_untrusted)
        logger.info(
            f"✅ Untrusted install processed (Policy: Allow+Log). Result: {status}"
        )
    except Exception as e:
        logger.info(f"ℹ️ Untrusted install blocked (Policy: Strict). Error: {e}")


if __name__ == "__main__":
    test_install()
