import requests
import json

try:
    print("Updating settings...")
    resp = requests.put('http://127.0.0.1:8765/settings', json={
        'voice': {'mock_stt': True, 'engine_preference': 'mock'}
    })
    print(f"Update: {resp.status_code}")
    print(resp.text)
    
    print("Health check...")
    health = requests.get('http://127.0.0.1:8765/voice/health').json()
    print(f"Engine: {health.get('stt_engine')}")
except Exception as e:
    print(f"Error: {e}")
