"""
W19 Verification - Crypto & Store.
"""

import os
import sys
import uuid

sys.path.append(os.getcwd())
from assistant.cloud.crypto import SyncCrypto
from assistant.cloud.local_store import LocalSyncStore
from assistant.cloud.snapshot import Snapshot

DB_PATH = os.path.join(os.getcwd(), "test_sync.db")


def test_sync_core():
    print("🧪 Testing Sync Core (Crypto + Store)...")

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    # 1. Crypto Test
    print("--- Crypto ---")
    crypto = SyncCrypto()
    payload = {"theme": "dark", "plugins": ["p1", "p2"]}
    print(f"Original: {payload}")

    encrypted = crypto.encrypt_payload(payload)
    print(f"Encrypted (len={len(encrypted)}): {encrypted[:20]}...")

    decrypted = crypto.decrypt_payload(encrypted)
    print(f"Decrypted: {decrypted}")

    if payload == decrypted:
        print("✅ Crypto Roundtrip Success.")
    else:
        print("❌ Crypto Mismatch.")

    # 2. Store Test
    print("\n--- Store ---")
    store = LocalSyncStore(DB_PATH)

    snap = Snapshot(
        snapshot_id=str(uuid.uuid4()),
        user_id="u_test",
        device_id="d_test",
        revision=1,
        encrypted_payload=encrypted,
    )

    store.save_snapshot(snap)
    print("Snapshot Saved.")

    latest = store.get_latest_snapshot()
    if latest:
        print(f"Latest Revision: {latest.revision}")
        if latest.snapshot_id == snap.snapshot_id:
            print("✅ Snapshot Retrieved Correctly.")
        else:
            print("❌ ID Mismatch.")
    else:
        print("❌ Failed to retrieve snapshot.")

    # Clean
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


if __name__ == "__main__":
    test_sync_core()
