"""
W17 Verification - Team Delegation.
"""

import json
import os
import socket
import sys
import threading
import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

sys.path.append(os.getcwd())
from assistant.main import app

# --- Mock Agent B ---
mock_b_received = []

app_b = FastAPI()


@app_b.post("/team/delegate")
async def b_delegate(req: Request):
    data = await req.json()
    print(f"[MOCK B] Received: {data}")
    mock_b_received.append(data)
    return {"status": "ok"}


def run_mock_b():
    # Start UDP Beacon for B
    def beacon():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        while True:
            try:
                msg = json.dumps(
                    {
                        "id": "agent-B",
                        "name": "Mock Agent B",
                        "ip": "127.0.0.1",
                        "port": 8768,  # B's Port
                        "role": "worker",
                    }
                ).encode("utf-8")
                sock.sendto(msg, ("224.0.0.1", 8767))
            except:
                pass
            time.sleep(2)

    threading.Thread(target=beacon, daemon=True).start()

    # Start HTTP for B
    uvicorn.run(app_b, host="127.0.0.1", port=8768, log_level="error")


def test_delegation():
    print("[TEST] Testing Team Delegation...")

    # 1. Start Mock B
    threading.Thread(target=run_mock_b, daemon=True).start()

    # 2. Start Agent A (TestClient)
    with TestClient(app) as client:
        print("Agent A Started.")

        # 3. Wait for Discovery
        print("Waiting for discovery (6s)...")
        time.sleep(6)

        # 4. Check Peers
        res = client.get("/team/peers")
        peers = res.json().get("peers", [])
        print(f"Peers Found: {[p['id'] for p in peers]}")

        target = next((p for p in peers if p["id"] == "agent-B"), None)
        if not target:
            print("[FAIL] Agent B not discovered!")
            return  # Fail

        print("[OK] Agent B Discovered.")

        # 5. Send Task
        print("Sending Task to Agent B...")
        res = client.post("/team/send_task?peer_id=agent-B&task=HelloB")
        print(f"Send Response: {res.json()}")

        if res.status_code == 200:
            print("[OK] Task Sent.")

            # 6. Verify B Received
            time.sleep(1)
            if mock_b_received:
                print(f"[OK] Mock B confirms receipt: {mock_b_received[0]}")
            else:
                print("[FAIL] Mock B did not receive task.")
        else:
            print("[FAIL] Send Failed.")


if __name__ == "__main__":
    test_delegation()
