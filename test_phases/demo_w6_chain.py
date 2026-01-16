"""
W6 Demonstration Script: Strategy Chain & Safety Wiring.

Verifies:
1. Session Auth (Auto-grant)
2. Executor Chain (UIA -> Coords)
3. Safety Triggers (UAC Simulation)
"""

import sys
import os
import time
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from assistant.session_auth import SessionAuth
from assistant.computer.windows import WindowsComputer
from assistant.safety.environment import EnvironmentMonitor
from assistant.safety.budget import ActionBudget
from assistant.executor.executor import ReliableExecutor
from assistant.executor.verify import Verifier
from assistant.executor.strategies import UIAStrategy, VisionStrategy, CoordsStrategy
from assistant.ui_contracts.schemas import ActionStep

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DemoW6")

def main():
    logger.info("=== Starting W6 Verification Demo ===")
    
    # 1. Initialize Components
    logger.info("Initializing components...")
    
    session_auth = SessionAuth()
    session_auth.grant() # Auto-grant for demo
    
    computer = WindowsComputer()
    computer.set_session_verifier(session_auth.ensure)
    
    environment = EnvironmentMonitor() 
    # Don't start monitoring thread, we'll check manually or let executor check
    
    budget = ActionBudget()
    verifier = Verifier(computer=computer)
    
    strategies = [
        UIAStrategy(),
        CoordsStrategy() # Vision skipped for demo speed/deps
    ]
    
    executor = ReliableExecutor(
        strategies=strategies,
        verifier=verifier,
        session_auth=session_auth,
        budget=budget,
        environment=environment
    )
    
    # 2. Define Test Plan
    steps = [
        ActionStep(
            id="1",
            tool="open_app",
            args={"app_name": "notepad.exe"},
            description="Open Notepad",
            verify={"type": "process_running", "value": "notepad.exe"}
        ),
        ActionStep(
            id="2",
            tool="type_text",
            args={"text": "Hello form W6 Chain!"},
            description="Type greeting",
            verify={"type": "window_title", "value": "Notepad"} # Simple verification
        )
    ]
    
    # 3. Execute Plan
    logger.info("Executing plan...")
    
    for step in steps:
        logger.info(f"\n--- Executing Step {step.id}: {step.description} ---")
        result = executor.execute(step)
        
        if result.success:
            logger.info(f"✅ Success! used strategy: {result.strategy_used}")
        else:
            logger.error(f"❌ Failed: {result.error}")
            if result.requires_takeover:
                logger.critical(f"🛑 TAKEOVER REQUIRED: {result.takeover_reason}")
                break
                
    # 4. Test Safety Trigger (Simulation)
    logger.info("\n--- Testing Safety Trigger (Simulated UAC) ---")
    
    # Mock environment to report secure desktop
    original_check = environment.check_state
    environment._is_secure_desktop = lambda: True 
    
    step_unsafe = ActionStep(id="3", tool="click", args={"x": 500, "y": 500}, description="Unsafe Click")
    
    result = executor.execute(step_unsafe)
    if not result.success and result.requires_takeover:
        logger.info("✅ Safety Trigger WORKED! Execution blocked due to Secure Desktop.")
    else:
        logger.error(f"❌ Safety Trigger FAILED. Result: {result}")

    logger.info("\n=== W6 Demo Complete ===")

if __name__ == "__main__":
    main()
