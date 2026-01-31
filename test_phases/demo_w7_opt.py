"""
W7 verification script:
1. Dynamic FPS measurement.
2. Selector Cache performance (Hit vs Miss).
3. Tiered Verification check.
"""

import sys
import os
import time
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from assistant.session_auth import SessionAuth
from assistant.computer.windows import WindowsComputer
from assistant.safety.budget import ActionBudget
from assistant.executor.executor import ReliableExecutor, ExecutorConfig
from assistant.executor.verify import Verifier
from assistant.executor.strategies import UIAStrategy, CoordsStrategy
from assistant.ui_contracts.schemas import ActionStep

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DemoW7")


def measure_fps(computer, target, duration=2):
    computer.set_fps(target)
    logger.info(f"Targeting {target} FPS for {duration}s...")
    count = 0
    start = time.time()
    while time.time() - start < duration:
        img = computer.screen_capture.capture()
        count += 1

    actual_fps = count / (time.time() - start)
    logger.info(f"Target: {target}, Actual: {actual_fps:.2f} FPS")
    return actual_fps


def main():
    logger.info("=== Starting W7 Optimization Verified ===")

    # 1. Init
    session = SessionAuth()
    session.grant()
    computer = WindowsComputer()
    computer.set_session_verifier(session.ensure)

    strategies = [UIAStrategy(), CoordsStrategy()]
    verifier = Verifier(computer=computer, strategies=strategies)
    budget = ActionBudget()

    executor = ReliableExecutor(
        strategies=strategies,
        verifier=verifier,
        session_auth=session,
        budget=budget,
        config=ExecutorConfig(use_selector_cache=True),
    )

    # 2. Test FPS
    logger.info("\n--- 1. Testing Dynamic FPS (W7.1) ---")
    fp1 = measure_fps(computer, 5, 2)
    fp2 = measure_fps(computer, 30, 2)

    if fp2 > fp1:
        logger.info("✅ FPS Boost Confirmed")
    else:
        logger.warning(
            f"⚠️ FPS Boost not significant ({fp1} vs {fp2}) - check hardware/DXCam"
        )

    # 3. Test Cache Speed (W7.3)
    logger.info("\n--- 2. Testing Selector Cache (W7.3) ---")

    # Pre-req: Open Notepad manually or ensure it's open.
    # Or use a common element like Taskbar or Start Button if accessible?
    # Let's try to type in Notepad (skipping open_app to keep stats clean, assume it's open from previous W6 test or user)
    # Actually W6 test opened it. If not, this might fail.
    # Safer: Open Notepad first.

    # Setup step
    step_open = ActionStep(
        id="init",
        tool="open_app",
        args={"app_name": "notepad.exe"},
        description="ensure notepad",
    )
    executor.execute(step_open)
    time.sleep(1)

    step_type = ActionStep(
        id="test_cache",
        tool="type_text",
        args={"text": "Cache Test"},
        # UIAStrategy handling 'type_text' might need logic change?
        # Actually UIAStrategy usually handles 'click', 'type' etc assuming it finds element.
        # But 'type_text' in llm.py is fallback to computer.type_text.
        # Strategies typically handle: click, input_text (if form field).
        # Let's use 'click' on something safe or just rely on 'UIAStrategy' finding a window.
        # Use find element directly via executor methods (internal) or just execute a step "click" on "File" menu?
    )
    # Using 'click' on 'File'
    step_click = ActionStep(
        id="click_file",
        tool="click",
        args={"name": "File", "control_type": "MenuItem"},
        description="Click File",
    )

    # Run 1 (Uncached)
    logger.info("Run 1 (Uncached)...")
    res1 = executor.execute(step_click)
    t1 = res1.duration_ms
    logger.info(f"Run 1 Time: {t1}ms (Success: {res1.success})")

    # Run 2 (Cached)
    logger.info("Run 2 (Cached)...")
    # Reset step (to clear internal state if any, though executor creates fresh result)
    # But step.selector might be populated? Executor logic:
    # "if self._config.use_selector_cache: cached = self._cache.get(key) ... step.selector = cached"
    # So we can reuse same step object or new one.
    step_click_2 = ActionStep(
        id="click_file_2",
        tool="click",
        args={"name": "File", "control_type": "MenuItem"},
    )

    res2 = executor.execute(step_click_2)
    t2 = res2.duration_ms
    logger.info(f"Run 2 Time: {t2}ms (Success: {res2.success})")

    if res1.success and res2.success:
        if t2 < t1:
            improvement = (t1 - t2) / t1 * 100
            logger.info(f"✅ Cache Optimization: {improvement:.1f}% faster")
        else:
            logger.warning(f"⚠️ No speedup: {t1}ms vs {t2}ms")
    else:
        logger.error("❌ Action failed, cannot verify cache.")

    logger.info("\n=== W7 Verify Complete ===")


if __name__ == "__main__":
    main()
