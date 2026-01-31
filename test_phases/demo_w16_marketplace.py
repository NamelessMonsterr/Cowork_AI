"""
W16 Verification - Marketplace Flow.
"""

import sys
import os
import shutil
from fastapi.testclient import TestClient

sys.path.append(os.getcwd())

from assistant.main import app
from assistant.marketplace.client import MarketplacePlugin
from assistant.plugins.signing import PluginSigner
from assistant.plugins.builder import PluginBuilder


# 1. Setup Dummy Plugin & Package
def setup_package():
    test_dir = "test_data_w16_mp"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    dist_dir = os.path.join(test_dir, "dist")

    # Generate Keys
    priv_path, pub_path = PluginSigner.generate_keys(test_dir)

    # Get Raw Public Key Hex (for registry)
    from cryptography.hazmat.primitives import serialization

    with open(pub_path, "rb") as f:
        # Load PEM to get object
        pub_key = PluginSigner.load_public_key(pub_path)
        # Get RAW bytes
        # Ed25519PublicKey.public_bytes(Raw, Raw)
        raw_bytes = pub_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        pub_key_hex = raw_bytes.hex()

    # Create Plugin
    src_dir = os.path.join(test_dir, "mp_plugin")
    os.makedirs(src_dir)
    import json

    with open(os.path.join(src_dir, "plugin.json"), "w") as f:
        json.dump(
            {
                "id": "com.cowork.mp_test",
                "version": "1.0.0",
                "name": "MP Test",
                "publisher": "CoworkAI Team",
            },
            f,
        )
    with open(os.path.join(src_dir, "main.py"), "w") as f:
        f.write("print('Marketplace Installed Me!')")

    # Build
    builder = PluginBuilder()
    pkg_path = builder.build_package(src_dir, priv_path, dist_dir)

    return pkg_path, pub_key_hex


async def mock_download(url, dest):
    print(f"[MOCK DOWNLOAD]: {url} -> {dest}")
    # URL is actually local path for test
    shutil.copy(url, dest)


def test_marketplace():
    print("[TEST] Testing Marketplace API & Install...")

    pkg_path, pub_key_hex = setup_package()
    print(f"Generated Package: {pkg_path}")
    print(f"Publisher Key: {pub_key_hex[:10]}...")

    # Mock Marketplace Client logic via Dependency Override or Monkeypatch
    from assistant.api.marketplace import mp_client

    # 1. Mock Registry Fetch
    original_fetch = mp_client.fetch_registry

    async def mock_fetch():
        return [
            MarketplacePlugin(
                id="com.cowork.mp_test",
                name="MP Test Plugin",
                version="1.0.0",
                description="Test",
                author="Tester",
                download_url=pkg_path,  # Local path as URL
                publisher_key=pub_key_hex,
            )
        ]

    mp_client.fetch_registry = mock_fetch
    mp_client.download_plugin = mock_download

    # 2. Test API
    with TestClient(app) as client:
        # List
        res = client.get("/marketplace/list")
        print(f"List Response: {res.status_code}")
        assert res.status_code == 200
        data = res.json()
        assert len(data["plugins"]) == 1
        print("[OK] List Plugins OK")

        # Install
        plugin_id = "com.cowork.mp_test"
        res = client.post(f"/marketplace/install/{plugin_id}")
        print(f"Install Response: {res.json()}")

        if res.status_code == 200:
            print("[OK] Install API OK")
            # Verify File System
            install_path = os.path.join(
                os.getenv("APPDATA"), "CoworkAI", "plugins", plugin_id
            )
            if os.path.exists(install_path):
                print(f"[OK] Plugin directory exists: {install_path}")
                if os.path.exists(os.path.join(install_path, "main.py")):
                    print("[OK] main.py verified.")
                else:
                    print("[FAIL] main.py missing!")
            else:
                print("[FAIL] Install directory missing!")
        else:
            print("[FAIL] Install Failed.")
            sys.exit(1)


if __name__ == "__main__":
    test_marketplace()
