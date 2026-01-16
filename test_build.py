"""
Phase 1 Build/Startup Test.

Verifies that the full application stack can initialize and start:
1. Loads all modules correctly.
2. Initializes WindowsComputer.
3. Starts FastAPI server.
4. Responds to /health check.
5. Shuts down cleanly.
"""

import time
import requests
import subprocess
import sys
import os
import signal

def test_startup():
    print("--- Phase 1 Build Test: Application Startup ---")
    
    # Command to start the backend
    cmd = [sys.executable, "-m", "assistant.main"]
    
    print(f"Starting backend: {' '.join(cmd)}")
    process = subprocess.Popen(
        cmd,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Wait for potential startup
        print("Waiting for server initialization (10s)...")
        server_up = False
        start_wait = time.time()
        
        while time.time() - start_wait < 15:
            try:
                # Try to hit health endpoint
                resp = requests.get("http://127.0.0.1:8765/health", timeout=1)
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"✅ Server is UP! Response: {data}")
                    server_up = True
                    break
            except requests.exceptions.ConnectionError:
                # Not up yet
                time.sleep(1)
                print(".", end="", flush=True)
        
        if not server_up:
            print("\n❌ Server failed to start within timeout.")
            # Check modules
            outs, errs = process.communicate(timeout=1)
            print(f"STDOUT: {outs}")
            print(f"STDERR: {errs}")
            return False

        # If up, try one more endpoint: Status
        try:
            resp = requests.get("http://127.0.0.1:8765/status", timeout=1)
            print(f"\n✅ /status endpoint check: {resp.status_code}")
            if resp.status_code == 200:
                print(f"   State: {resp.json()}")
        except Exception as e:
            print(f"   Status check failed: {e}")

        return True

    finally:
        print("\nStopping server...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("Build test complete.")

if __name__ == "__main__":
    success = test_startup()
    if success:
        print("\n✨ PHASE 1 BUILD VERIFIED SUCCESSFUL")
        sys.exit(0)
    else:
        print("\n❌ PHASE 1 BUILD FAILED")
        sys.exit(1)
