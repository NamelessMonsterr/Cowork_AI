"""
LLM Client - Brain of the Operation.
Now Powered by OpenAI GPT-4.
"""

import os
import logging
import json
import base64
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger("LLM")

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    logger.warning("openai not installed. Run: pip install openai")

class AgentResponse(BaseModel):
    thought: str
    reply_text: Optional[str] = None
    plan: List[Dict[str, Any]]
    needs_more_info: bool = False

class LLMClient:
    def __init__(self):
        # OpenAI API Key provided by user
        self.api_key = "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"
        
        if HAS_OPENAI:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def analyze_screen_and_plan(
        self, 
        task: str, 
        screenshot_path: Optional[str] = None,
        context: str = ""
    ) -> AgentResponse:
        
        # === LOCAL-FIRST: Try rule-based fallback before hitting API ===
        # This saves API calls for common commands like "open notepad", "open chrome", etc.
        local_plan = self.detect_intent_fallback(task)
        if local_plan:
            logger.info(f"✅ Local rules matched for: {task} (No API call needed)")
            return AgentResponse(
                thought="Used local rules for common command.",
                plan=local_plan,
                reply_text="Processing locally."
            )
        
        # === API FALLBACK: Only call OpenAI for complex/unknown commands ===
        if not self.client:
            logger.warning("OpenAI not available and no local rules matched.")
            return AgentResponse(
                thought="No matching local rules and OpenAI not installed.",
                plan=[],
                reply_text="Command not recognized. Try: 'open notepad' or 'open chrome'."
            )

        logger.info(f"🌐 No local rules matched. Calling OpenAI for: {task}")

        system_prompt = """You are a Windows Automation Agent (like Jarvis). 
Break down the user request into executable actions.

Available actions: 
- launch_app(app_name) - Open an application (notepad, chrome, calc, etc.)
- click(target) - Click on a UI element
- type_text(text) - Type text into focused window
- press_keys(keys) - Press keyboard shortcuts (ctrl+s, alt+tab, etc.)
- wait(seconds) - Wait for specified seconds
- speak(text) - Say something to the user
- run_command(command) - Execute a shell command (PowerShell)

You MUST respond with valid JSON in this exact format:
{
    "thought": "your reasoning about what to do",
    "reply_text": "optional message to speak to user",
    "plan": [
        {"action": "launch_app", "target": "notepad"},
        {"action": "type_text", "value": "Hello World"},
        {"action": "speak", "value": "Done!"}
    ]
}"""

        user_prompt = f"User Task: {task}\nContext: {context}"

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Add screenshot if available
            if screenshot_path and os.path.exists(screenshot_path):
                with open(screenshot_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                messages[1] = {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                    ]
                }

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            logger.info(f"LLM Response: {content}")

            data = json.loads(content)
            return AgentResponse(**data)

        except Exception as e:
            logger.error(f"OpenAI Call failed: {e}")
            # Final fallback - return empty plan with helpful message
            return AgentResponse(
                thought=f"API error: {e}",
                plan=[],
                reply_text="I couldn't process that command. Try simpler commands like 'open notepad'."
            )

    def detect_intent_fallback(self, user_text: str) -> Optional[List[Dict[str, Any]]]:
        """
        Use centralized actions registry for local command matching.
        To add new actions, edit: assistant/agent/actions.py
        """
        from assistant.agent.actions import match_action
        return match_action(user_text)

    def _get_fallback_plan(self, task: str) -> List[Dict[str, Any]]:
        # Alias for backward compatibility if needed
        return self.detect_intent_fallback(task) or []

