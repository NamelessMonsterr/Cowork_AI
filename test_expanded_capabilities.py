"""
Verification tests for expanded PlanGuard capabilities.
Tests safe app opening, URL validation, and dangerous command blocking.
"""

import requests

API_URL = "http://127.0.0.1:8765"


def test_apis():
    """Test safety API endpoints."""
    print("\n=== Testing Safety APIs ===")

    # Test trusted apps
    r = requests.get(f"{API_URL}/safety/trusted_apps")
    if r.status_code == 200:
        apps = r.json()
        print(f"✅ Trusted apps loaded: {len(apps.get('trusted_apps', []))} apps")
        print(f"   Chrome in list: {'chrome' in str(apps).lower()}")
        print(f"   VS Code in list: {'code' in str(apps).lower()}")
    else:
        print(f"❌ Failed to load trusted apps: {r.status_code}")

    # Test trusted domains
    r = requests.get(f"{API_URL}/safety/trusted_domains")
    if r.status_code == 200:
        domains = r.json()
        print(f"✅ Trusted domains loaded: {len(domains.get('trusted_domains', []))} domains")
        print(f"   github.com in list: {'github.com' in str(domains)}")
    else:
        print(f"❌ Failed to load trusted domains: {r.status_code}")


def test_safe_commands():
    """Test that safe commands work."""
    print("\n=== Testing Safe Commands ===")

    # Grant session
    requests.post(f"{API_URL}/permission/grant")

    # Test 1: Open Chrome
    print("\n1. Testing: 'Open Chrome'")
    r = requests.post(f"{API_URL}/plan/preview", json={"task": "Open Chrome"})
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ Plan preview generated: {data.get('plan_id')}")
        print(f"   Steps: {len(data.get('plan', {}).get('steps', []))}")
    else:
        print(f"   ❌ Preview failed: {r.status_code}")

    # Test 2: Open VS Code
    print("\n2. Testing: 'Open VS Code'")
    r = requests.post(f"{API_URL}/plan/preview", json={"task": "Open VS Code"})
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ Plan preview generated: {data.get('plan_id')}")
    else:
        print(f"   ❌ Preview failed: {r.status_code}")

    # Test 3: Open github.com
    print("\n3. Testing: 'Open github.com'")
    r = requests.post(f"{API_URL}/plan/preview", json={"task": "Open github.com"})
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ Plan preview generated: {data.get('plan_id')}")
    else:
        print(f"   ❌ Preview failed: {r.status_code}")


def test_blocked_commands():
    """Test that dangerous commands are blocked."""
    print("\n=== Testing Blocked Commands ===")

    # Grant session
    requests.post(f"{API_URL}/permission/grant")

    # Test 1: PowerShell (untrusted app)
    print("\n1. Testing: 'Open PowerShell' (should be blocked)")
    r = requests.post(f"{API_URL}/plan/preview", json={"task": "Open PowerShell"})
    data = r.json()
    plan_id = data.get("plan_id")

    # Try to approve (should reject)
    r = requests.post(f"{API_URL}/plan/approve", json={"plan_id": plan_id})
    if r.status_code == 400 or "violations" in str(r.text).lower():
        print("   ✅ Correctly blocked PowerShell")
    else:
        print(f"   ❌ PowerShell was NOT blocked! Status: {r.status_code}")

    # Test 2: Untrusted domain
    print("\n2. Testing: 'Open example.com' (should be blocked)")
    r = requests.post(f"{API_URL}/plan/preview", json={"task": "Open example.com"})
    data = r.json()
    plan_id = data.get("plan_id")

    r = requests.post(f"{API_URL}/plan/approve", json={"plan_id": plan_id})
    if r.status_code == 400 or "violations" in str(r.text).lower():
        print("   ✅ Correctly blocked untrusted domain")
    else:
        print("   ❌ Untrusted domain was NOT blocked!")

    # Test 3: Shell command
    print("\n3. Testing: 'Run cmd' (should be blocked)")
    r = requests.post(f"{API_URL}/plan/preview", json={"task": "Run cmd command dir"})
    data = r.json()
    plan_id = data.get("plan_id")

    r = requests.post(f"{API_URL}/plan/approve", json={"plan_id": plan_id})
    if r.status_code == 400 or "violations" in str(r.text).lower():
        print("   ✅ Correctly blocked shell command")
    else:
        print("   ❌ Shell command was NOT blocked!")


if __name__ == "__main__":
    print("=" * 60)
    print("PLANGU ARD EXPANSION VERIFICATION")
    print("=" * 60)

    try:
        test_apis()
        test_safe_commands()
        test_blocked_commands()

        print("\n" + "=" * 60)
        print("✅ VERIFICATION COMPLETE")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        print("Make sure backend is running: python run_backend.py")
