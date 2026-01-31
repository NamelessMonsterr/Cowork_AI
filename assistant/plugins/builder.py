"""
Plugin Builder (W16.1).
Packages a plugin directory into a signed .cowork-plugin file.
Format:
- wrapper.zip (.cowork-plugin)
  - content.zip (Source code)
  - signature.hex (Ed25519 signature of content.zip)
  - manifest.json (Copy of plugin.json)
"""

import json
import logging
import os
import shutil
import zipfile

from assistant.plugins.signing import PluginSigner

logger = logging.getLogger("PluginBuilder")


class PluginBuilder:
    def __init__(self):
        pass

    def build_package(self, source_dir: str, private_key_path: str, output_dir: str) -> str:
        """
        Build a signed plugin package.
        Returns path to the created .cowork-plugin file.
        """
        if not os.path.exists(os.path.join(source_dir, "plugin.json")):
            raise ValueError("Source directory missing plugin.json")

        # 1. Read Manifest
        with open(os.path.join(source_dir, "plugin.json")) as f:
            manifest_data = json.load(f)
            plugin_id = manifest_data.get("id", "unknown")
            version = manifest_data.get("version", "0.0.1")

        # Prepare Output
        os.makedirs(output_dir, exist_ok=True)
        temp_dir = os.path.join(output_dir, f"temp_{plugin_id}")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # 2. Create content.zip
            content_zip_path = os.path.join(temp_dir, "content.zip")
            self._zip_directory(source_dir, content_zip_path)

            # 3. Sign content.zip
            signature = PluginSigner.sign_file(content_zip_path, private_key_path)
            sig_path = os.path.join(temp_dir, "signature.hex")
            with open(sig_path, "w") as f:
                f.write(signature)

            # 4. Copy Manifest
            manifest_path = os.path.join(temp_dir, "manifest.json")
            shutil.copy(os.path.join(source_dir, "plugin.json"), manifest_path)

            # 5. Create Final Package
            package_name = f"{plugin_id}-{version}.cowork-plugin"
            final_path = os.path.join(output_dir, package_name)

            with zipfile.ZipFile(final_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(content_zip_path, arcname="content.zip")
                zf.write(sig_path, arcname="signature.hex")
                zf.write(manifest_path, arcname="manifest.json")

            logger.info(f"✅ Plugin built: {final_path}")
            return final_path

        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def _zip_directory(self, source_dir, zip_path):
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    # Skip hidden/system files
                    if file.startswith(".") or file.endswith(".pyc"):
                        continue

                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, source_dir)
                    zf.write(full_path, arcname=rel_path)
