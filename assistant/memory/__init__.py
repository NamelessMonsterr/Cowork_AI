"""
Memory Module - Task Memory and Context Awareness.

Provides:
- TaskMemory: Persistent task history and learning
- ContextAwareness: Active app and clipboard tracking
"""

from .task_memory import (
    TaskMemory,
    TaskRecord,
    ActionPattern,
)

from .context import (
    ContextAwareness,
    AppContext,
    ClipboardContent,
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
