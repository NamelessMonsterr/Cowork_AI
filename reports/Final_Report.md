# Final Report: Root Cause Analysis of UI vs Terminal Discrepancy

## Executive Summary

The "works in terminal, fails in UI" issue is caused by a **configuration divergence between the Test Environment (Benchmark CLI) and the Production Environment (Main Backend).**

Specifically, the logic to execute OS-level commands (`open_app`, `run_shell`) was implemented **only within the test harness**, effectively "mocking" the capability for the benchmark without actually adding it to the main application.

## Detailed Findings

### 1. The "Ghost" Strategy

In the previous session, to pass the benchmark suite, a class named `SystemStrategy` was dynamically defined (inlined) inside `assistant/benchmark/harness.py`.

**`assistant/benchmark/harness.py` (Test Environment):**

```python
# ... inside the harness ...
class SystemStrategy(Strategy):
    def can_handle(self, step): return step.tool in ["open_app", "run_shell"]
    # ... implementation calling WindowsComputer ...

strategies = [
    SystemStrategy(computer),  # <--- INJECTED HERE
    UIAStrategy(),
    # ...
]
```

This strategy acts as the bridge between the high-level `open_app` tool and the low-level `WindowsComputer` functions.

### 2. The Missing Link in Production

The main application entry point, `assistant/main.py`, configures the `ReliableExecutor` with a hardcoded list of strategies.

**`assistant/main.py` (Production Environment):**

```python
# ... initialization ...
strategies = [
    UIAStrategy(),
    VisionStrategy(),
    CoordsStrategy()
]
# ... SystemStrategy is COMPLETELY MISSING here
```

Because `SystemStrategy` was never saved to a file (e.g., `assistant/executor/strategies/system.py`) and never imported into `main.py`, the real application **literally does not know how to open applications or run shell commands**, even though the low-level `WindowsComputer` has the code to do it.

### 3. Why the Terminal Works

When you run:
`python -m assistant.benchmark.cli --suite 10_tasks.yaml`

You are running the **Benchmark Harness**. This harness:

1.  Detects the missing capability.
2.  dynamically injects the `SystemStrategy` "patch" into memory.
3.  Runs the test successfully using this patch.

### 4. Why the UI Fails

When you run:
`npm start` (Frontend) + `python -m uvicorn assistant.main:app` (Backend)

You are running the **Production App**. This app:

1.  Loads `assistant/main.py`.
2.  Loads only `UIA` and `Vision` strategies.
3.  Receives a command like "Open Notepad".
4.  Planner creates a step: `{"tool": "open_app", "args": {"app_name": "notepad"}}`.
5.  Executor asks its strategies: "Who can handle 'open_app'?"
    - `UIAStrategy`: "No."
    - `VisionStrategy`: "No."
    - `CoordsStrategy`: "No."
6.  **Result:** "All strategies failed." -> Crash/Failure.

## Conclusion

The system successfully passed the benchmark because the test runner was "smarter" than the actual application. The fix implemented previously was a **test-side fix**, not a **product-side fix**.

## Required Remediation

To enable the UI to work as well as the terminal, the following engineering steps are required:

1.  **Extract**: Move `SystemStrategy` from `harness.py` to a dedicated file `assistant/executor/strategies/system.py`.
2.  **Register**: Import `SystemStrategy` in `assistant/main.py` and add it to the `strategies` list.
3.  **Verify**: Restart the backend and verify that `open_app` works via the UI.
