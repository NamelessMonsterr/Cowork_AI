from assistant.safety.session_auth import SessionAuth
from assistant.ui_contracts.schemas import ActionStep, ConfigDict

# Check if import works (Bug 3)
from assistant.computer import Computer


def test_bug_1_session_auth_check_exists():
    """Verify SessionAuth.check() exists and works."""
    auth = SessionAuth()
    assert hasattr(auth, "check"), "SessionAuth missing check() method"
    assert auth.check() is False, "Should be False by default"
    auth.grant()
    assert auth.check() is True, "Should be True after grant"
    auth.revoke()
    assert auth.check() is False


def test_bug_2_pydantic_config():
    """Verify Schemas use ConfigDict."""
    # Inner Config class should be gone or ignored in favor of model_config
    assert isinstance(ActionStep.model_config, dict) or isinstance(
        ActionStep.model_config, ConfigDict
    )
    # use_enum_values should be set
    assert ActionStep.model_config.get("use_enum_values") is True


def test_bug_3_test_computers_import():
    """Verify test_computers.py import path is correct."""
    assert Computer is not None
