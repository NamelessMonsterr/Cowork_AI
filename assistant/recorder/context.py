"""
Recoder Context - Captures environmental anchors for robustness (W8).

Each step is anchored to:
- Active Window Title
- Process Name
- Monitor Index

This "Anchor" allows the Replay engine to find the correct target
even if the window moves or changes size.
"""

from typing import Optional, Dict
from dataclasses import dataclass, asdict
import time

try:
    import psutil
    from assistant.computer.windows import WindowsComputer, WindowInfo
except ImportError:
    pass

@dataclass
class ContextAnchor:
    timestamp: float
    window_title: str
    process_name: str
    process_id: int
    monitor_idx: int = 0
    rect: tuple = (0, 0, 0, 0)
    
    def to_dict(self):
        return asdict(self)

class ContextTracker:
    def __init__(self, computer: "WindowsComputer"):
        self.computer = computer

    def capture_anchor(self) -> ContextAnchor:
        """Capture current context anchor."""
        win_info = self.computer.get_active_window()
        
        title = "Unknown"
        pid = -1
        proc_name = "Unknown"
        rect = (0, 0, 0, 0)
        
        if win_info:
            title = win_info.title
            pid = win_info.process_id
            rect = win_info.rect
            
            try:
                proc = psutil.Process(pid)
                proc_name = proc.name()
            except:
                pass
                
        # Monitor logic placeholder (assume 0 for now or derive from rect)
        monitor_idx = 0 
        
        return ContextAnchor(
            timestamp=time.time(),
            window_title=title,
            process_name=proc_name,
            process_id=pid,
            monitor_idx=monitor_idx,
            rect=rect
        )
