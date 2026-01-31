"""
Diagnostics Module (W15.3).
Export comprehensive support bundles for debugging.
"""

import datetime
import json
import logging
import os
import platform
import zipfile

logger = logging.getLogger("Diagnostics")


class DiagnosticsManager:
    def __init__(self):
        self.app_data = os.path.join(os.getenv("APPDATA"), "CoworkAI")
        self.logs_dir = os.path.join(self.app_data, "logs")
        self.config_dir = os.path.join(self.app_data, "plugins")  # Configs are here

        # Ensure export dir
        self.export_dir = os.path.join(self.app_data, "exports")
        os.makedirs(self.export_dir, exist_ok=True)

    def create_bundle(self) -> str:
        """
        Create a diagnostic zip bundle.
        Returns absolute path to the zip file.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"flash_diagnostics_{timestamp}.zip"
        zip_path = os.path.join(self.export_dir, zip_name)

        logger.info(f"Creating diagnostics bundle: {zip_path}")

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # 1. System Info (Sanitized)
                sys_info = {
                    "platform": platform.platform(),
                    "python": platform.python_version(),
                    "timestamp": timestamp,
                    "version": "1.0.0-beta",  # TODO: Dynamic version
                }
                zf.writestr("system_info.json", json.dumps(sys_info, indent=2))

                # 2. Logs (Recent only)
                if os.path.exists(self.logs_dir):
                    for file in os.listdir(self.logs_dir):
                        if file.endswith(".log") or file.endswith(".jsonl"):
                            full_path = os.path.join(self.logs_dir, file)
                            zf.write(full_path, arcname=f"logs/{file}")

                # 3. Config (Sanitized - NO SECRETS)
                # We skip secrets.json intentionally
                if os.path.exists(self.config_dir):
                    for file in os.listdir(self.config_dir):
                        if file in ["enabled.json", "trusted.json"]:
                            full_path = os.path.join(self.config_dir, file)
                            zf.write(full_path, arcname=f"config/{file}")

            return zip_path

        except Exception as e:
            logger.error(f"Failed to create diagnostics: {e}")
            raise e
