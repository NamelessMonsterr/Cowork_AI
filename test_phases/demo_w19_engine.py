"""
W19 Verification - Sync Engine.
"""

import sys
import os
import uuid

sys.path.append(os.getcwd())
from assistant.cloud.local_store import LocalSyncStore
from assistant.cloud.crypto import SyncCrypto
from assistant.cloud.sync_engine import SyncEngine
from assistant.cloud.auth import AuthUser
import assistant.cloud.auth as auth_module

DB_PATH = os.path.join(os.getcwd(), "test_sync_engine.db")


def test_engine():
    print("🧪 Testing Sync Engine...")

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    # 1. Mock Auth
    auth_module.current_user = AuthUser(
        user_id="u_test", email="test@cowork.ai", token="t1"
    )

    # 2. Init Engine
    store = LocalSyncStore(DB_PATH)
    crypto = SyncCrypto()
    engine = SyncEngine(store, crypto)

    # 3. Push Rev 1
    state_v1 = {"settings": {"theme": "light"}}
    print("Pushing V1...")
    engine.push(state_v1)

    # Check Revision
    last_rev = store.get_last_revision()
    print(f"Local Revision: {last_rev}")
    if last_rev == 1:
        print("✅ Push V1 OK.")
    else:
        print("❌ Push V1 Failed.")

    # 4. Pull (Should be no-op)
    res = engine.pull()
    if res is None:
        print("✅ Pull (Up to date) OK.")
    else:
        print("❌ Pull unexpected result.")

    # 5. Simulate Cloud Update (Another Device)
    print("\n--- Simulating Remote Device Push ---")

    payload_v2 = {"settings": {"theme": "dark"}}
    enc_v2 = crypto.encrypt_payload(payload_v2)
    snap_v2 = engine._get_cloud_head()
    # Create valid V2 snapshot
    from assistant.cloud.snapshot import Snapshot

    remote_snap = Snapshot(
        snapshot_id=str(uuid.uuid4()),
        user_id="u_test",
        device_id="d_other",
        revision=2,
        encrypted_payload=enc_v2,
    )
    # Manually inject into engine's cloud mock
    engine.cloud_mock_snapshots.append(remote_snap)
    print("Remote pushed V2.")

    # 6. Pull V2
    print("Pulling...")
    new_state = engine.pull()
    if new_state and new_state["settings"]["theme"] == "dark":
        print("✅ Pull V2 Success (Theme updated to dark).")
        print(f"Local Revision Now: {store.get_last_revision()}")
    else:
        print(f"❌ Pull V2 Failed. Got: {new_state}")

    # Cleanup
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


if __name__ == "__main__":
    test_engine()
