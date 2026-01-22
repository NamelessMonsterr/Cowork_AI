import logging
logging.basicConfig(level=logging.INFO)
from unittest import mock
import sys
import traceback
from assistant.ui_contracts.schemas import ExecutionPlan, ActionStep

def debug_planguard():
    print("--- Debugging PlanGuard ---")
    try:
        from assistant.safety.plan_guard import PlanGuard, PlanGuardConfig, PlanValidationError
        config = PlanGuardConfig(
            allowed_tools=["open_url"],
            trusted_domains=["example.com"]
        )
        mock_auth = mock.Mock()
        guard = PlanGuard(mock_auth, config)
        
        # Test IP Block
        steps = [ActionStep(id="1", tool="open_url", args={"url": "http://1.1.1.1"})]
        plan = ExecutionPlan(id="p1", task="t", steps=steps)
        try:
            guard.validate(plan)
            print("FAIL: Should block IP")
        except PlanValidationError:
            print("PASS: IP blocked")
            
        # Test Trusted Block
        steps = [ActionStep(id="2", tool="open_url", args={"url": "http://evil.com"})]
        plan = ExecutionPlan(id="p2", task="t", steps=steps)
        try:
            guard.validate(plan)
            print("FAIL: Should block untrusted")
            print("Violations:", config.trusted_domains)
        except PlanValidationError:
            print("PASS: Untrusted domain blocked")
            
    except Exception:
        traceback.print_exc()

def debug_shell():
    print("--- Debugging RestrictedShell ---")
    try:
        from assistant.safety.shell_validator import RestrictedShellValidator
        v = RestrictedShellValidator()
        if not v.validate("cmd", "echo hello"):
            print("FAIL: safe command rejected")
        if v.validate("cmd", "echo hello | whoami"):
             print("FAIL: pipe allowed")
        else:
             print("PASS: pipe blocked")
             
        from assistant.tools.restricted_shell import RestrictedShellTool
        t = RestrictedShellTool({"enabled": True})
        try:
            t._validate_command("cmd", "echo hello | whoami", False, False)
            print("FAIL: Tool allowed pipe")
        except Exception:
            print("PASS: Tool blocked pipe")
            
    except Exception:
        traceback.print_exc()

def debug_audio():
    print("--- Debugging AudioRecorder ---")
    try:
        from assistant.voice.audio_recorder import AudioRecorder
        # Just init check
        with mock.patch("assistant.voice.audio_recorder.sd") as mock_sd:
             r = AudioRecorder()
             print("PASS: AudioRecorder Init")
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    debug_planguard()
    debug_shell()
    debug_audio()
