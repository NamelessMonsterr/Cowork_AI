"""
W15 Verification - Diagnostics API.
"""

import io
import os
import sys
import zipfile

from fastapi.testclient import TestClient

# Add project root needed for imports
sys.path.append(os.getcwd())


def test_diagnostics():
    from assistant.main import app

    print("🧪 Testing Diagnostics Export...")

    with TestClient(app) as client:
        # Mock some logs if needed, but app likely has some
        response = client.get("/support/diagnostics")

        if response.status_code != 200:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            sys.exit(1)

        print("✅ API returned 200 OK")

        # Validate Zip
        try:
            zip_bytes = io.BytesIO(response.content)
            with zipfile.ZipFile(zip_bytes) as zf:
                files = zf.namelist()
                print(f"📦 Zip Contents: {files}")

                if "system_info.json" not in files:
                    print("❌ Missing system_info.json")
                    sys.exit(1)

                print("✅ Zip structure valid.")
        except Exception as e:
            print(f"❌ Invalid Zip: {e}")
            sys.exit(1)


if __name__ == "__main__":
    test_diagnostics()
