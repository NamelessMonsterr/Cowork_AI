"""
W19.5 Sync Engine.
Orchestrates Snapshot Push/Pull and Conflict Resolution.
"""

import logging
import uuid
from typing import Optional, Dict, Any

from assistant.cloud.snapshot import Snapshot
from assistant.cloud.crypto import SyncCrypto
from assistant.cloud.local_store import LocalSyncStore
from assistant.cloud.auth import get_current_user

logger = logging.getLogger("SyncEngine")


class SyncEngine:
    def __init__(self, store: LocalSyncStore, crypto: SyncCrypto):
        self.store = store
        self.crypto = crypto
        self.device_id = str(uuid.uuid4())  # In real app, persist this

        # In-memory Cloud Mock
        self.cloud_mock_snapshots = []  # List of Snapshot objects

    def _get_cloud_head(self) -> Optional[Snapshot]:
        """Mock: Get latest from cloud."""
        if not self.cloud_mock_snapshots:
            return None
        return sorted(self.cloud_mock_snapshots, key=lambda x: x.revision)[-1]

    def _push_to_cloud(self, snap: Snapshot):
        """Mock: Push to cloud."""
        # Simple rule: Must be > current head revision
        head = self._get_cloud_head()
        if head and snap.revision <= head.revision:
            raise ValueError("Conflict: Cloud has newer or equal revision.")

        self.cloud_mock_snapshots.append(snap)
        logger.info(f"☁️ Pushed Revision {snap.revision} to Cloud.")

    def push(self, current_state: Dict[str, Any]):
        """Capture state and push."""
        user = get_current_user()
        if not user:
            logger.warning("Push failed: Not logged in.")
            return

        # 1. Determine Revision
        local_rev = self.store.get_last_revision()
        cloud_head = self._get_cloud_head()

        if cloud_head and cloud_head.revision > local_rev:
            # We are behind. Conflict? Or just pull first.
            # For MVP: Fail push, tell user to pull.
            logger.warning("Push failed: Client is behind cloud. Pull first.")
            return

        new_rev = local_rev + 1

        # 2. Encrypt
        encrypted_payload = self.crypto.encrypt_payload(current_state)

        # 3. Create Snapshot
        snap = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            user_id=user.user_id,
            device_id=self.device_id,
            revision=new_rev,
            encrypted_payload=encrypted_payload,
        )

        # 4. Save Local & Push
        try:
            self._push_to_cloud(snap)
            self.store.save_snapshot(snap, applied=True)  # It reflects our state
            logger.info(f"✅ Sync Push Success: Rev {new_rev}")
        except Exception as e:
            logger.error(f"Sync Push Failed: {e}")

    def pull(self) -> Optional[Dict[str, Any]]:
        """Pull latest and return decrypted payload if newer."""
        user = get_current_user()
        if not user:
            return None

        cloud_head = self._get_cloud_head()
        if not cloud_head:
            logger.info("Cloud empty.")
            return None

        local_rev = self.store.get_last_revision()

        if cloud_head.revision > local_rev:
            logger.info(
                f"⬇️ Pulling Revision {cloud_head.revision} (Local: {local_rev})..."
            )

            # Decrypt
            try:
                payload = self.crypto.decrypt_payload(cloud_head.encrypted_payload)

                # Update Local Store
                self.store.save_snapshot(
                    cloud_head, applied=True
                )  # Assuming we apply it immediately

                return payload
            except Exception as e:
                logger.error(f"Decryption failed: {e}")
                return None

        logger.info("Already up to date.")
        return None
