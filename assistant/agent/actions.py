"""
Actions Registry - Single source of truth for all local actions.

To add a new action:
1. Add a regex pattern
2. Add the handler function
3. Register it in ACTIONS list

That's it! No other files to edit.
"""

import re
import logging
from typing import Optional, List, Dict, Any, Callable

logger = logging.getLogger("Actions")

# ==================== ACTION HANDLERS ====================
# Each handler receives (computer, tts, value) and returns True on success

async def handle_open_app(computer, tts, target, value):
    """Launch an application."""
    computer.launch_app(target)
    return True

async def handle_take_screenshot(computer, tts, target, value):
    """Take a screenshot."""
    path = computer.take_screenshot()
    logger.info(f"Screenshot saved: {path}")
    await tts.speak("Screenshot taken")
    return True

async def handle_type_text(computer, tts, target, value):
    """Type text into active window."""
    computer.type_text(value or target)
    return True

async def handle_press_keys(computer, tts, target, value):
    """Press keyboard shortcut."""
    computer.press_keys(value or target)
    return True

async def handle_wait(computer, tts, target, value):
    """Wait for specified seconds."""
    import asyncio
    await asyncio.sleep(float(value or 1.0))
    return True

async def handle_speak(computer, tts, target, value):
    """Speak text to user."""
    await tts.speak(value)
    return True


# ==================== ACTIONS REGISTRY ====================
# Format: (regex_pattern, action_name, target, speak_message, extra_steps)
# extra_steps is a list of additional steps to add after the main action

ACTIONS = [
    # App Launchers
    {
        "pattern": r"\b(open|launch|start)\s+notepad\b",
        "action": "open_app",
        "target": "notepad",
        "speak": "Opening Notepad",
        "supports_type": True,  # Can chain "and type X"
    },
    {
        "pattern": r"\b(open|launch|start)\s+(google\s+)?(chrome|browser|internet)\b",
        "action": "open_app",
        "target": "chrome",
        "speak": "Opening Chrome",
        "supports_type": True,
    },
    {
        "pattern": r"\b(open|launch|start)\s+(calc|calculator)\b",
        "action": "open_app",
        "target": "calc",
        "speak": "Opening Calculator",
    },
    {
        "pattern": r"\b(open|launch|start)\s+(code|vscode|visual studio code)\b",
        "action": "open_app",
        "target": "code",
        "speak": "Opening VS Code",
    },
    {
        "pattern": r"\b(open|show)\s+(downloads)\b",
        "action": "open_app",
        "target": "explorer",
        "speak": "Opening Downloads",
    },
    # Screenshot
    {
        "pattern": r"\b(take|capture|save)\s+(a\s+)?(screenshot|screen|snap)\b",
        "action": "take_screenshot",
        "target": None,
        "speak": "Taking screenshot",
    },
    # Volume Control (NEW - example of easy addition)
    {
        "pattern": r"\b(mute|unmute)\s*(volume|sound|audio)?\b",
        "action": "press_keys",
        "target": "volume_mute",
        "speak": "Toggling mute",
    },
    {
        "pattern": r"\b(volume\s+up|increase\s+volume|louder)\b",
        "action": "press_keys",
        "target": "volume_up",
        "speak": "Volume up",
    },
    {
        "pattern": r"\b(volume\s+down|decrease\s+volume|quieter)\b",
        "action": "press_keys",
        "target": "volume_down",
        "speak": "Volume down",
    },
    # Lock Screen
    {
        "pattern": r"\b(lock)\s+(screen|computer|pc)\b",
        "action": "press_keys", 
        "target": "win+l",
        "speak": "Locking computer",
    },
    # Greetings
    {
        "pattern": r"\b(hello|hi|hey|greetings|good morning|good evening)\b",
        "action": "speak",
        "target": None,
        "speak": "Greetings. I am online and ready.",
    },
    # Media Controls
    {
        "pattern": r"\b(play|pause|stop)\s+(music|song|media|video)?\b",
        "action": "press_keys",
        "target": "playpause",
        "speak": "Toggling playback",
    },
    {
        "pattern": r"\b(next|skip)\s+(song|track|video)?\b",
        "action": "press_keys",
        "target": "nexttrack",
        "speak": "Skipping track",
    },
    {
        "pattern": r"\b(previous|back)\s+(song|track|video)?\b",
        "action": "press_keys",
        "target": "prevtrack",
        "speak": "Previous track",
    },
]

# Dangerous patterns to block
DANGEROUS_KEYWORDS = [
    "format", "rm -rf", "delete system32", "shutdown", 
    "install", "pip install", "sudo", "regedit"
]

# Action handlers map
HANDLERS = {
    "open_app": handle_open_app,
    "take_screenshot": handle_take_screenshot,
    "type_text": handle_type_text,
    "press_keys": handle_press_keys,
    "wait": handle_wait,
    "speak": handle_speak,
}


def match_action(user_text: str) -> Optional[List[Dict[str, Any]]]:
    """
    Match user text against registered actions.
    Returns a plan (list of steps) or None if no match.
    
    IMPORTANT: Steps use 'tool' and 'args' keys to match ActionStep schema.
    """
    text = user_text.lower().strip()
    
    # Safety check
    if any(k in text for k in DANGEROUS_KEYWORDS):
        logger.warning(f"Blocked dangerous command: {text}")
        return None
    
    step_id = 1
    
    # Try each pattern
    for action_def in ACTIONS:
        pattern = re.compile(action_def["pattern"])
        if pattern.search(text):
            plan = []
            
            # Main action - use 'tool' and 'args' to match ActionStep schema
            main_step = {
                "id": str(step_id),
                "tool": action_def["action"],
                "args": {},
                "description": action_def.get("speak", "")
            }
            if action_def.get("target"):
                main_step["args"]["target"] = action_def["target"]
            plan.append(main_step)
            step_id += 1
            
            # Speak confirmation
            plan.append({
                "id": str(step_id),
                "tool": "speak",
                "args": {"text": action_def["speak"]},
                "description": "Confirmation"
            })
            step_id += 1
            
            # Check for "and type..." suffix
            if action_def.get("supports_type"):
                type_match = re.search(r"(?:(?:and|then)\s+type\s+)(.+)$", text)
                if type_match:
                    to_type = type_match.group(1).strip().strip('"\'')
                    plan.append({
                        "id": str(step_id),
                        "tool": "wait",
                        "args": {"seconds": 4.0},
                        "description": "Wait for app to open"
                    })
                    step_id += 1
                    plan.append({
                        "id": str(step_id),
                        "tool": "type_text",
                        "args": {"text": to_type},
                        "description": f"Type: {to_type}"
                    })
            
            logger.info(f"✅ Matched action: {action_def['action']} for '{text}'")
            return plan
    
    return None


async def execute_action(action_name: str, computer, tts, target=None, value=None) -> bool:
    """Execute a single action by name."""
    handler = HANDLERS.get(action_name)
    if handler:
        return await handler(computer, tts, target, value)
    else:
        logger.warning(f"Unknown action: {action_name}")
        return False
