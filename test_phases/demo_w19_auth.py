"""
W19 Verification - Cloud Identity.
"""

import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.getcwd())
os.environ["COWORK_TEST_MODE"] = "true"  # Disable heavy startup
from assistant.cloud.auth import OTP_STORE
from assistant.main import app


def test_auth():
    print("[TEST] Testing Cloud Auth...")

    with TestClient(app) as client:
        email = "test@cowork.ai"

        # 1. Request OTP
        print(f"Requesting OTP for {email}...")
        res = client.post("/cloud/auth/request_otp", json={"email": email})
        assert res.status_code == 200
        print("[OK] OTP Requested.")

        # 2. Get OTP (Backdoor)
        otp_data = OTP_STORE.get(email)
        if not otp_data:
            print("[FAIL] OTP not found in store.")
            return
        otp = otp_data["otp"]
        print(f"[DEBUG] OTP is: {otp}")

        # 3. Verify OTP
        print("Verifying OTP...")
        res = client.post("/cloud/auth/verify_otp", json={"email": email, "otp": otp})
        assert res.status_code == 200
        user = res.json()
        print(f"[OK] Logged in as: {user['user_id']}")

        # 4. Check Status
        res = client.get("/cloud/auth/status")
        status = res.json()
        if status.get("authenticated") and status["user"]["email"] == email:
            print("[OK] Status: Authenticated")
        else:
            print(f"[FAIL] Check Status Failed: {status}")

        # 5. Logout
        print("Logging out...")
        client.post("/cloud/auth/logout")
        res = client.get("/cloud/auth/status")
        if not res.json().get("authenticated"):
            print("[OK] Logout Successful.")
        else:
            print("[FAIL] Still authenticated.")


if __name__ == "__main__":
    test_auth()
