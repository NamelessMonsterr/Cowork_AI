from assistant.safety.plan_guard import PlanGuard, PlanGuardConfig
from unittest import mock
import sys

print("Checking PlanGuardConfig...")
try:
    config = PlanGuardConfig(
        allowed_tools=["open_url"],
        trusted_domains=["example.com"]
    )
    print("Config created successfully:", config.trusted_domains)
except Exception as e:
    print("FAILED Config:", e)
    sys.exit(1)

print("Checking PlanGuard Init...")
try:
    mock_auth = mock.Mock()
    guard = PlanGuard(mock_auth, config)
    print("PlanGuard initialized.")
    print("Guard trusted domains:", guard.trusted_domains)
except Exception as e:
    print("FAILED Init:", e)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("Checking Validate...")
class MockStep:
    def __init__(self, tool, args):
        self.tool = tool
        self.args = args
        self.retries = 0

plan = [MockStep("open_url", {"url": "https://example.com"})]
try:
    guard.validate(plan)
    print("Validate success")
except Exception as e:
    print("FAILED Validate:", e)
    import traceback
    traceback.print_exc()
