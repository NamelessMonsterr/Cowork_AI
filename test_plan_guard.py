import requests
import json
import time

BASE_URL = "http://127.0.0.1:8765"

def test_safe_command():
    """Test 1: Safe command should execute."""
    print("🧪 Test 1: Safe command (Open Notepad and type hello)")
    
    # Grant permission
    r = requests.post(f"{BASE_URL}/permission/grant")
    print(f"✅ Permission granted: {r.json()}")
    time.sleep(0.5)
    
    # Get plan preview
    r = requests.post(f"{BASE_URL}/plan/preview", json={"task": "Open Notepad and type hello"})
    data = r.json()
    plan_id = data["plan_id"]
    print(f"Plan ID: {plan_id}")
    print(f"Steps: {len(data['plan']['steps'])}")
    time.sleep(0.5)
    
    # Approve plan
    r = requests.post(f"{BASE_URL}/plan/approve", json={"plan_id": plan_id})
    result = r.json()
    print(f"Result: {result}")
    print("")

def test_dangerous_command():
    """Test 2: Dangerous command should be rejected."""
    print("🧪 Test 2: Dangerous command (Open PowerShell)")
    
    # Grant permission
    r = requests.post(f"{BASE_URL}/permission/grant")
    print(f"✅ Permission granted")
    time.sleep(0.5)
    
    # Get plan preview
    r = requests.post(f"{BASE_URL}/plan/preview", json={"task": "Open PowerShell"})
    data = r.json()
    plan_id = data["plan_id"]
    print(f"Plan ID: {plan_id}")
    time.sleep(0.5)
    
    # Try to approve plan
    r = requests.post(f"{BASE_URL}/plan/approve", json={"plan_id": plan_id})
    result = r.json()
    print(f"Result: {result}")
    print("")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing PlanGuard Allowlist Fixes")
    print("=" * 60)
    print("")
    
    try:
        test_safe_command()
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        print("")
    
    try:
        test_dangerous_command()
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        print("")
    
    print("=" * 60)
    print("Tests complete. Check backend logs for detailed output.")
    print("=" * 60)
