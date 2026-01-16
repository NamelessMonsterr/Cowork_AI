"""
Plugin Installer (W13.2).

Handles installation of plugins from .zip files.
Responsibilities:
1. Validate Zip integrity.
2. Check for Path Traversal (Security).
3. Validate Manifest (plugin.json).
4. Verify Publisher Trust (W13.3).
5. Unpack to %APPDATA%/CoworkAI/plugins/.
"""

import os
import io
import json
import zipfile
import logging
import shutil
from typing import Dict, Any, Tuple
from assistant.plugins.manifest import PluginManifest
from assistant.plugins.registry import TRUSTED_PUBLISHERS
from assistant.plugins.signing import PluginSigner

logger = logging.getLogger("PluginInstaller")

class PluginInstaller:
    def __init__(self):
        self.install_dir = os.path.join(os.getenv('APPDATA'), 'CoworkAI', 'plugins')
        os.makedirs(self.install_dir, exist_ok=True)
        
    def install_zip(self, zip_bytes: bytes) -> Tuple[str, str]: # returns (plugin_id, status)
        """
        Install a plugin from zip bytes.
        Returns: plugin_id, status_message
        """
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                # 1. Security Check: Path Traversal
                for info in zf.infolist():
                    if ".." in info.filename or os.path.isabs(info.filename):
                        raise ValueError(f"Security Violation: Invalid path '{info.filename}'")
                
                # 2. Find manifest
                if "plugin.json" not in zf.namelist():
                    raise ValueError("Invalid Plugin: plugin.json missing at root.")
                    
                # 3. Read & Validate Manifest
                with zf.open("plugin.json") as f:
                    data = json.load(f)
                    
                manifest = PluginManifest(**data) # Validates schema
                
                # 4. Check Trust
                if manifest.publisher not in TRUSTED_PUBLISHERS:
                    # In MVP we block or warn. 
                    # Per W13 spec: state = BLOCKED_UNTRUSTED, but we allow install?
                    # Let's install but log warning. The Lifecycle/API will handle enablement gating.
                    logger.warning(f"Installing untrusted plugin from {manifest.publisher}")
                
                # 5. Extract
                # Create folder ID (sanitize?)
                target_dir = os.path.join(self.install_dir, manifest.id)
                
                if os.path.exists(target_dir):
                     # Overwrite? Or Error? MVP: Backup/Overwrite or Error.
                     # Let's Error for safety to prevent accidental nuke.
                     # raise ValueError(f"Plugin {manifest.id} already installed. Remove first.")
                     # Actually update is needed. Let's nuke and replace.
                     shutil.rmtree(target_dir)
                     
                os.makedirs(target_dir)
                zf.extractall(target_dir)
                
                logger.info(f"✅ Plugin {manifest.id} installed to {target_dir}")
                return manifest.id, "success"
                
        except Exception as e:
            logger.error(f"Install Failed: {e}")
            raise e

    def install_package(self, package_path: str, public_key_hex: str = None) -> Tuple[str, str]:
        """
        Install a signed .cowork-plugin package.
        """
        if not os.path.exists(package_path):
            raise FileNotFoundError(f"Package not found: {package_path}")
            
        try:
            with zipfile.ZipFile(package_path, 'r') as zf:
                # 1. Check Structure
                files = zf.namelist()
                if "content.zip" not in files or "signature.hex" not in files:
                    raise ValueError("Invalid Package: Missing content.zip or signature.hex")
                
                # 2. Extract to Temp for Verification
                # We need files on disk for verify_file (or update verifier to take bytes? verify_file takes path)
                # Let's extract to temp dir
                temp_extract = package_path + "_extract"
                os.makedirs(temp_extract, exist_ok=True)
                zf.extractall(temp_extract)
                
                content_path = os.path.join(temp_extract, "content.zip")
                sig_path = os.path.join(temp_extract, "signature.hex")
                
                # 3. Verify Signature
                with open(sig_path, 'r') as f:
                    sig_hex = f.read().strip()
                
                if public_key_hex:
                    logger.info("🔐 Verifying Plugin Signature...")
                    valid = PluginSigner.verify_with_raw_hex(content_path, sig_hex, public_key_hex)
                    if not valid:
                        raise ValueError(f"❌ Signature Verification FAILED for package {package_path}. Aborting.")
                    logger.info("✅ Signature Verified.")
                else:
                    logger.warning(f"⚠️ Installing Unverified Package (No Publisher Key Provided): {package_path}")

                # To invoke install_inner:
                with open(content_path, 'rb') as f:
                    content_bytes = f.read()
                    
                return self.install_zip(content_bytes)

        except Exception as e:
            logger.error(f"Package Install Failed: {e}")
            raise e
        finally:
             if 'temp_extract' in locals() and os.path.exists(temp_extract):
                 shutil.rmtree(temp_extract)
