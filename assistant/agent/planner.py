"""
Planner Module - Orchestrates high-level logic.

1. Receives user request
2. Gets computer state (Screenshot + Window info)
3. Consults LLM
4. Generates Execution Plan
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from assistant.computer.windows import WindowsComputer
from assistant.agent.llm import LLMClient, AgentResponse
from assistant.voice.tts import TTS

logger = logging.getLogger("Planner")

class Planner:
    def __init__(self):
        self.computer = WindowsComputer()
        self.llm = LLMClient() 
        self.tts = TTS()
        
    async def create_plan(self, user_task: str) -> List[Dict[str, Any]]:
        """
        Generate a plan for the user task based on current state.
        """
        logger.info(f"Planning for task: {user_task}")
        
        # 1. Observe
        screenshot_path = self.computer.take_screenshot()
        active_window = self.computer.get_active_window()
        
        context = f"Active APP: {active_window.title if active_window else 'None'}"
        
        # 2. Think (LLM)
        response: AgentResponse = self.llm.analyze_screen_and_plan(
            task=user_task,
            screenshot_path=screenshot_path,
            context=context
        )
        
        logger.info(f"LLM Thought: {response.thought}")
        
        plan = response.plan
        

        
        # 3. Handle Voice Reply
        # If the LLM wants to say something (clarification or narration), 
        # we add it as a "speak" step at the start.
        if response.reply_text:
            speak_step = {
                "action": "speak",
                "target": "user",
                "value": response.reply_text
            }
            # Prepend to plan
            plan.insert(0, speak_step)

        # 4. Clean up screenshot
        if screenshot_path and "screenshot_" in screenshot_path:
             try:
                 pass 
             except: 
                 pass

        return plan

    async def execute_step(self, step: Dict[str, Any]):
        """
        Execute a single planned step using Computer.
        """
        action = step.get("action")
        target = step.get("target") 
        value = step.get("value")   
        
        logger.info(f"Executing: {action} -> {target}")


        
        if action == "launch_app":
            self.computer.launch_app(target)
            
        elif action == "type_text":
            self.computer.type_text(value or target)
            
        elif action == "press_keys":
            self.computer.press_keys(value or target)
            
        elif action == "click":
            # Real implementation would use coordinate finding strategies here
            pass

        elif action == "speak":
            # New Voice capability
            await self.tts.speak(value)
            
        elif action == "wait":
            import time
            time.sleep(float(value or 1.0))
            
        elif action == "take_screenshot":
            path = self.computer.take_screenshot()
            logger.info(f"Screenshot saved to: {path}")
            await self.tts.speak("Screenshot taken")
            
        elif action == "run_command":
            logger.info(f"Running shell command: {value}")
            self.computer.run_shell_command(value)
            await self.tts.speak("Executing command")

        else:
            logger.warning(f"Unknown action: {action}")
