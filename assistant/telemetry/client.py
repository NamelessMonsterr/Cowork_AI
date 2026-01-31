"""
Privacy-First Telemetry (W15.5).
Collects anonymized usage stats (success/fail rates, timings)
ONLY if user opts in.
"""

import os
import json
import logging
import uuid
import time
from typing import Dict, Any

logger = logging.getLogger("Telemetry")


class TelemetryClient:
    def __init__(self):
        self.enabled = False
        self.session_id = str(uuid.uuid4())
        self.buffer = []
        self._load_config()

    def _load_config(self):
        # Check enabled.json or separate telemetry.json
        # For now, we assume explicit enable via API/File
        # Default is False (Privacy First)
        config_path = os.path.join(os.getenv("APPDATA"), "CoworkAI", "telemetry.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                    self.enabled = data.get("enabled", False)
            except:
                pass

        if self.enabled:
            logger.info(f"Telemetry ENABLED. Session: {self.session_id}")
        else:
            logger.info("Telemetry DISABLED (Opt-in required).")

    def track(self, event: str, properties: Dict[str, Any] = None):
        if not self.enabled:
            return

        payload = {
            "event": event,
            "session_id": self.session_id,
            "timestamp": time.time(),
            "properties": properties or {},
        }

        # Sanitize Payload (Double Check)
        # Remove potentially sensitive keys if accidental
        self._sanitize(payload)

        self.buffer.append(payload)

        # Flush if buffer gets big (Mock flush)
        if len(self.buffer) >= 10:
            self.flush()

    def _sanitize(self, payload):
        """Ensure no obvious PII in properties."""
        props = payload.get("properties", {})
        keys_to_remove = [
            "text",
            "input",
            "screenshot",
            "clipboard",
            "password",
            "token",
        ]
        for k in list(props.keys()):
            if any(s in k.lower() for s in keys_to_remove):
                del props[k]

    def flush(self):
        """Send data to server (Mock)."""
        if not self.buffer:
            return

        logger.info(f"📡 Telemetry Flush: {len(self.buffer)} events")
        # In real impl, POST to https://telemetry.cowork.ai
        self.buffer.clear()

    def enable(self):
        self.enabled = True
        self._save_config()

    def disable(self):
        self.enabled = False
        self._save_config()

    def _save_config(self):
        config_path = os.path.join(os.getenv("APPDATA"), "CoworkAI", "telemetry.json")
        try:
            with open(config_path, "w") as f:
                json.dump({"enabled": self.enabled}, f)
        except:
            pass
