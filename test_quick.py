import requests

print("Testing expanded parser...")

tests = [
    "type Hello from the new parser!",
    "screenshot",
    "open calc",
    "wait 1",
]

for cmd in tests:
    print(f"\nTesting: {cmd}")
    r = requests.post("http://localhost:8765/just_do_it", json={"task": cmd})
    print(f"  Result: {r.json()}")
