"""
Clipboard Plugin - Reference Implementation (W12.7).

Provides tools to read/write clipboard.
"""

from typing import Dict, Any, List
import pyperclip
from assistant.plugins.sdk import Plugin, Tool, ToolSpec, ToolContext

class ReadClipboardTool(Tool):
    def __init__(self):
        super().__init__(ToolSpec(
            name="read_clipboard",
            description="Read text from the system clipboard",
            input_schema={},
            output_schema={"type": "string"},
            risk_level="low",
            requires_secrets=[] 
        ))

    async def run(self, args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
        text = pyperclip.paste()
        return {"content": text}

class WriteClipboardTool(Tool):
    def __init__(self):
        super().__init__(ToolSpec(
            name="write_clipboard",
            description="Write text to the system clipboard",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"}
                },
                "required": ["text"]
            },
            risk_level="medium", # Modifies state
            requires_secrets=[]
        ))

    async def run(self, args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
        text = args.get("text", "")
        pyperclip.copy(text)
        return {"status": "success", "length": len(text)}

class ClipboardPlugin(Plugin):
    def get_tools(self) -> List[Tool]:
        return [ReadClipboardTool(), WriteClipboardTool()]
