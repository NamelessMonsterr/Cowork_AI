"""
Memory Module - Task Memory and Context Awareness.

Provides:
- TaskMemory: Persistent task history and learning
- ContextAwareness: Active app and clipboard tracking
"""

from .context import (
    AppContext,
    ClipboardContent,
    ContextAwareness,
)
from .task_memory import (
    ActionPattern,
    TaskMemory,
    TaskRecord,
)

__all__ = [
    # Task Memory
    "TaskMemory",
    "TaskRecord",
    "ActionPattern",
    # Context
    "ContextAwareness",
    "AppContext",
    "ClipboardContent",
]
