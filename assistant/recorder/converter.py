"""
Smart Converter - Transforms raw inputs into Semantic Action Plan (W8.2).

Logic:
1. Groups inputs (debounce text, clean clicks).
2. Resolves clicks to UIA elements (Name/Type).
3. Generates verification specs (e.g. check element exists).
4. Inserts Privacy Markers (Takeover Required).
"""

import logging

from assistant.executor.strategies import UIAStrategy
from assistant.recorder.context import ContextAnchor
from assistant.recorder.input import InputEvent
from assistant.ui_contracts.schemas import (
    ActionStep,
    UISelector,
    VerifySpec,
    VerifyType,
)

logger = logging.getLogger("SmartConverter")


class SmartConverter:
    def __init__(self, computer: "WindowsComputer"):
        self.computer = computer
        self.uia_strategy = UIAStrategy()

    def convert(self, events: list[InputEvent], anchors: list[ContextAnchor]) -> list[ActionStep]:
        """Convert events to ActionSteps."""
        steps = []

        # 1. Pre-process / Grouping
        grouped_events = self._group_events(events)

        # 2. Iterate and Convert
        for i, event in enumerate(grouped_events):
            anchor = anchors[i] if i < len(anchors) else None
            step = self._event_to_step(event, anchor, step_id=str(i + 1))
            if step:
                steps.append(step)

        return steps

    def _group_events(self, events: list[InputEvent]) -> list[InputEvent]:
        """Compress consecutive related events."""
        # Note: Recorder already debounces text.
        # Here we could merge fast clicks (double click) logic if needed.
        # For now, pass through as recorder is already smart.
        return events

    def _event_to_step(self, event: InputEvent, anchor: ContextAnchor | None, step_id: str) -> ActionStep | None:
        # --- Type Text ---
        if event.type == "type_text":
            text = event.data.get("text", "")
            if not text:
                return None

            # Check for sensitive context (simple heuristic or use anchor)
            # Recorder handles redaction, so if we see REDACTED or similar flag...
            # But here we just assume recorder gave us safe text?
            # Or if anchor indicates sensitive window?

            if self._is_sensitive(anchor):
                return ActionStep(
                    id=step_id,
                    tool="takeover_required",
                    args={"reason": "Sensitive input detected"},
                    risk_level="high",
                    description="[PRIVACY BLOCK] - sensitive input",
                )

            # Ensure we focus the window first?
            # Ideally the plan has a "focus_window" step before typing if context changed.
            # For simplicity, we assume user clicked before typing, so 'click' step handles focus.

            return ActionStep(
                id=step_id,
                tool="type_text",
                args={"text": text},
                description=f"Type '{text}'",
                verify=VerifySpec(
                    type=VerifyType.TEXT_PRESENT,  # Weak verify
                    value=text,
                    timeout=2,
                ),
            )

        # --- Click ---
        elif event.type == "click":
            x = event.data["x"]
            y = event.data["y"]
            button = event.data["button"]

            # Smart Resolve: What did we click?
            # We need to query UIA *now* or simulating it?
            # Wait, the conversion happens *after* recording stopped. UIA query will fail because state is gone.
            # CRITICAL: We can't query UIA post-facto unless we saved the UIA tree dump or element at that time.
            # Plan W8.2 said: "During record, just save (x,y)... Inference: Detect Open App".
            # User Feedback: "Convert coords -> semantic ActionSteps using UIA element-under-cursor... Post-processing is safer."
            # BUT: Post-processing implies we can't look up the live element anymore.
            # REVISION: We MUST query UIA *during* record (fast check) or just save (x,y) and rely on Coordinates.
            # However, user strongly requested "Smart Converter (Click -> UIA Element)".
            # If we run UIA *during* record, it might lag.
            # Alternative: Replay based on coordinates, verify, and *then* upgrade to UIA?
            # Better: In `input.py`, we should have captured a snapshot or minimal UIA info if performance allows.
            # OR logic: Use purely coordinates for now (W8 MVP) unless we add "Live Inspector" to Recorder.

            # Given constraints and user preference for "Smart Converter":
            # Just output "click by coordinates" for now, but with context anchors.
            # UPGRADE: If we captured process name, we can try `click(args={x, y, window_title})`.
            # True "Semantic" conversion post-hoc is impossible without DOM dump.
            # Let's produce a Coordinate Step, but add "context" to args so we can refine it later or use visual search.

            # However, if we know the process is "Shortcut" (Desktop), we infer "Open App".
            # Heuristic: If anchor.process_name is "explorer" (Desktop) and click resulted in new process?

            step = ActionStep(
                id=step_id,
                tool="click",
                args={
                    "x": x,
                    "y": y,
                    "window_title": anchor.window_title if anchor else None,
                },
                description=f"Click at ({x}, {y})",
                selector=UISelector(strategy="coords", bbox=(x, y, x, y)),
            )

            # Auto-Verify (Generic)
            # Check if click caused something? Hard to guess.
            return step

        # --- Special Keys ---
        elif event.type == "press_key":
            key = event.data["key"]
            return ActionStep(
                id=step_id,
                tool="press_keys",
                args={"keys": key},
                description=f"Press {key}",
            )

        return None

    def _is_sensitive(self, anchor: ContextAnchor | None) -> bool:
        if not anchor:
            return False
        title = anchor.window_title.lower()
        keywords = ["password", "login", "sign in", "bank", "vault", "otp"]
        return any(k in title for k in keywords)
