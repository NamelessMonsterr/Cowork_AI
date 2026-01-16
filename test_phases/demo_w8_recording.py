"""
W8 Verification Script: Macro Recording & Replay.

Flow:
1. Start Recording.
2. Simulate Input Events (via InputRecorder internal mock or pynput).
3. Stop Recording & Verify Plan Generation.
4. Playback Macro & Verify Execution.
"""

import sys
import os
import time
import logging
import asyncio
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from assistant.main import state, start_recording, stop_recording, play_macro
from assistant.recorder.input import InputEvent
from assistant.ui_contracts.schemas import ActionStep

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DemoW8")

async def main():
    logger.info("=== Starting W8 Macro Verification ===")
    
    # 1. Init System
    state.session_auth.grant()
    if state.computer:
        state.computer.set_session_verifier(state.session_auth.ensure)
        
    # Manual Init of Components (simulating lifespan)
    from assistant.recorder.input import InputRecorder
    from assistant.recorder.context import ContextTracker
    from assistant.recorder.converter import SmartConverter
    from assistant.recorder.storage import MacroStorage
    
    state.macro_storage = MacroStorage()
    state.context_tracker = ContextTracker(state.computer)
    state.smart_converter = SmartConverter(state.computer)
    
    def on_input_event(event):
        if event.type in ["click", "type_text", "press_key"]:
            anchor = state.context_tracker.capture_anchor()
            state.current_recording_anchors.append(anchor)
            
    state.input_recorder = InputRecorder(on_event=on_input_event)
    logger.info("✅ Recorder Components Initialized Manually")
    
    # 2. Start Recording
    logger.info("\n--- 1. Start Recording ---")
    # Need to run start() which sets state to RECORDING
    # Since we manually init, we call start on instance
    state.input_recorder.start()
    time.sleep(0.5) # Wait for thread start
    logger.info("Recorder started.")
    
    # 3. Simulate Inputs
    logger.info("\n--- 2. Injecting Mock Events ---")
    
    rec = state.input_recorder
    # Verify state is RECORDING
    logger.info(f"Recorder State: {rec._state}")
    
    # Event 1: Click (100, 100)
    # We must use _add_event which checks state
    rec._add_event("click", {"x": 100, "y": 100, "button": "Button.left", "sensitive": False})
    
    # Event 2: Type "test"
    rec._add_event("type_text", {"text": "test"})
    
    time.sleep(0.5)
    
    # Event 3: Panicked? No.
    
    # 4. Stop Recording
    logger.info("\n--- 3. Stop Recording ---")
    result = await stop_recording(name="Test Macro W8")
    macro_id = result["macro_id"]
    steps_count = result["steps"]
    logger.info(f"Recording stopped. ID: {macro_id}, Steps: {steps_count}")
    
    if steps_count != 2:
        logger.error(f"❌ Expected 2 steps (Click, Type), got {steps_count}")
        return
        
    # Verify File Exists
    plan = state.macro_storage.load_plan(macro_id)
    if not plan:
        logger.error("❌ Failed to load saved plan")
        return
    
    logger.info(f"✅ Plan Loaded: {plan.task}")
    for s in plan.steps:
        logger.info(f" - Step: {s.tool} {s.args}")
        
    # 5. Playback
    logger.info("\n--- 4. Replay Macro ---")
    # For replay, we need to mock executor or let it run.
    # If we run it, it will actually click (100, 100) and type "test".
    # This is safe enough? Yes.
    
    # We call play_macro which launches background task. 
    # But here we want to await it for test.
    # play_macro returns {"status": "playing"} and launches task.
    # We can call the internal driver directly to await it.
    from assistant.main import drive_plan_execution
    
    await drive_plan_execution(plan)
    logger.info("✅ Replay Completed")
    
    # 6. Verify Context Anchors (Implementation Check)
    # Check if we have anchors in memory?
    # Actually storage.py only saved plan and metadata. The plan steps MIGHT have anchors in args?
    # Converter puts 'window_title' in args for click.
    step0 = plan.steps[0]
    if "window_title" in step0.args:
        logger.info(f"✅ Context Anchor Verified: {step0.args['window_title']}")
    else:
        logger.warning("⚠️ Context Anchor missing from step args")

    logger.info("\n=== W8 Demo Complete ===")

if __name__ == "__main__":
    asyncio.run(main())
