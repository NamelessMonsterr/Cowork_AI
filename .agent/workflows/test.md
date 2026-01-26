---
description: Test generation and test running command. Creates and executes tests for code.
---

# /test - Test Generation and Execution

$ARGUMENTS

---

## Purpose

This command generates tests, runs existing tests, or checks test coverage for the Flash Assistant project.

---

## Sub-commands

```
/test                - Run all tests (107 pytest tests)
/test [file/feature] - Generate tests for specific target
/test coverage       - Show test coverage report
/test unit           - Run unit tests only
/test security       - Run security tests only
/test fix            - Fix failing tests
```

---

## Project Test Info

- **Framework**: pytest 7.4.4
- **Total Tests**: 107 (41 unit, 50+ security, 10+ integration)
- **Test Runner**: `python -m pytest tests/`
- **Coverage Tool**: `pytest-cov`

---

## Behavior

### Run Tests (No Arguments)

When `/test` is called alone:

1. **Execute full test suite**

   ```bash
   python -m pytest tests/ -v --tb=short
   ```

2. **Report results**
   - Tests passed/failed
   - Collection errors
   - Execution time

3. **Highlight failures**
   - Show failed test names
   - Display assertion errors
   - Suggest fixes

### Generate Tests

When asked to test a file or feature:

1. **Analyze the code**
   - Identify functions and methods
   - Find edge cases
   - Detect dependencies to mock

2. **Generate test cases**
   - Happy path tests
   - Error cases
   - Edge cases
   - Integration tests (if needed)

3. **Write tests**
   - Use pytest framework
   - Follow existing test patterns in `tests/`
   - Mock external dependencies
   - Use AAA pattern (Arrange-Act-Assert)

---

## Output Format

### For Test Execution

```
🧪 Running Flash Assistant Test Suite...

tests/unit/test_config.py::test_load_settings ✅ PASSED
tests/unit/test_security_fixes.py::test_no_shell_injection ✅ PASSED
tests/test_restricted_shell_policy.py::test_dangerous_commands ✅ PASSED
tests/integration/test_api.py::test_permission_grant ❌ FAILED

Failed:
  ✗ test_permission_grant
    AssertionError: assert 200 == 403
    Expected session check to fail, got success

=== 106 passed, 1 failed in 12.34s ===

Coverage: 78%
```

### For Test Generation

```markdown
## 🧪 Tests: assistant/main.py auto-revoke bug

### Test Plan

| Test Case                   | Type | Coverage   |
| --------------------------- | ---- | ---------- |
| Session persists after task | Unit | Happy path |
| Session respects TTL        | Unit | Validation |
| Manual revoke works         | Unit | Edge case  |

### Generated Tests

`tests/unit/test_session_persistence.py`

[Code block with tests]

---

Run with: `python -m pytest tests/unit/test_session_persistence.py -v`
```

---

## Examples

```
/test                                    # Run all 107 tests
/test assistant/main.py                  # Generate tests for main.py
/test session auto-revoke bug            # Generate test for specific bug
/test coverage                           # Show coverage report
/test unit                               # Run unit tests only
/test fix                                # Fix failing tests
```

---

## Common Commands

### Run Specific Test Suites

```bash
# Unit tests only (41 tests)
python -m pytest tests/unit/ -v

# Security tests
python -m pytest tests/test_restricted_shell_policy.py tests/test_hardening.py -v

# Integration tests
python -m pytest tests/integration/ -v

# Single test file
python -m pytest tests/unit/test_security_fixes.py -v

# Specific test
python -m pytest tests/unit/test_config.py::test_load_settings -v
```

### Debug & Coverage

```bash
# With coverage report
python -m pytest tests/ --cov=assistant --cov-report=html

# Stop on first failure
python -m pytest tests/ -x

# Verbose with full tracebacks
python -m pytest tests/ -vv --tb=long

# Collect tests without running
python -m pytest tests/ --collect-only
```

---

## Test Patterns

### Unit Test Structure (pytest)

```python
import pytest
from assistant.safety.session_auth import SessionAuth

class TestSessionAuth:
    """Test session authentication logic."""

    def test_grant_creates_active_session(self):
        """Should create an active session when granted."""
        # Arrange
        auth = SessionAuth()

        # Act
        auth.grant(mode="session", ttl_sec=1800)

        # Assert
        assert auth.check() is True
        assert auth.mode == "session"

    def test_session_expires_after_ttl(self):
        """Should expire session after TTL passes."""
        # Arrange
        auth = SessionAuth()
        auth.grant(mode="session", ttl_sec=1)  # 1 second TTL

        # Act
        import time
        time.sleep(2)  # Wait for expiry

        # Assert
        assert auth.check() is False

    def test_revoke_clears_session(self):
        """Should immediately clear session when revoked."""
        # Arrange
        auth = SessionAuth()
        auth.grant(mode="session", ttl_sec=1800)

        # Act
        auth.revoke()

        # Assert
        assert auth.check() is False
```

### Integration Test Structure

```python
import pytest
from fastapi.testclient import TestClient
from assistant.main import app

class TestPermissionAPI:
    """Test permission-related API endpoints."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_grant_permission_returns_200(self, client):
        """Should grant permission and return 200."""
        # Arrange
        payload = {"mode": "session", "ttl_sec": 1800}

        # Act
        response = client.post("/permission/grant", json=payload)

        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "granted"
```

---

## Key Principles

- **Test behavior not implementation**
- **One assertion per test** (when practical)
- **Descriptive test names** (use docstrings)
- **Arrange-Act-Assert pattern** (AAA)
- **Mock external dependencies** (use `pytest-mock`)
- **Fixture reuse** for common setup
- **Parametrize** for similar test cases

---

## Current Test Status

- **Total Tests**: 107 collected
- **Passing**: Unit tests & Security tests
- **Failing**: Integration tests blocked by collection error (Exit Code 2)
- **Known Issues**:
  - Terminal encoding in PowerShell (use `run_tests.py`)
  - Integration `test_security_fixes.py` needs better isolation
