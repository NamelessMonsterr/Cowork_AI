# Test: /just_do_it endpoint
import requests
import time

time.sleep(2)  # Wait for server

try:
    r = requests.post(
        "http://localhost:8765/just_do_it", json={"task": "open notepad"}, timeout=3
    )
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
except Exception as e:
    print(f"Error: {e}")
