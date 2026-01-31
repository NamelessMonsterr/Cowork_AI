"""
Input Recorder - Captures user actions for Macro Learning (W8).

Features:
- Global Mouse/Keyboard hooks (pynput).
- Privacy: Redacts inputs on sensitive windows.
- Privacy: Hotkeys (Start/Stop, Pause, Panic).
- Debouncing: Type text aggregation.
"""

import logging
import threading
import time
from collections.abc import Callable
from enum import Enum

try:
    from pynput import keyboard, mouse

    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

logger = logging.getLogger("RecorderInput")


class RecorderState(Enum):
    STOPPED = "stopped"
    RECORDING = "recording"
    PAUSED = "paused"


class InputEvent:
    def __init__(self, event_type: str, data: dict, timestamp: float = None):
        self.type = event_type
        self.data = data
        self.timestamp = timestamp or time.time()

    def __repr__(self):
        return f"Event({self.type}, {self.data})"


class InputRecorder:
    def __init__(
        self,
        on_event: Callable[[InputEvent], None] | None = None,
        check_privacy_func: Callable[[], bool] | None = None,
    ):
        self._state = RecorderState.STOPPED
        self._events: list[InputEvent] = []
        self._start_time = 0
        self._lock = threading.Lock()

        # Hooks
        self._mouse_listener = None
        self._key_listener = None

        # Privacy & Callbacks
        self._on_event = on_event
        self._check_privacy = check_privacy_func  # Returns True if sensitive window active
        self._is_sensitive = False

        # Debouncing
        self._last_key_time = 0
        self._current_text = []  # Buffer for typing

        if not HAS_PYNPUT:
            logger.error("pynput not installed. Recorder will not function.")

    def start(self):
        """Start recording."""
        if not HAS_PYNPUT:
            return

        with self._lock:
            if self._state == RecorderState.RECORDING:
                return

            self._events = []
            self._start_time = time.time()
            self._state = RecorderState.RECORDING
            self._current_text = []

            # Start Listeners
            self._mouse_listener = mouse.Listener(on_click=self._on_click, on_scroll=self._on_scroll)
            self._key_listener = keyboard.Listener(on_press=self._on_key_press, on_release=self._on_key_release)

            self._mouse_listener.start()
            self._key_listener.start()
            logger.info("Recorder started.")

    def stop(self) -> list[InputEvent]:
        """Stop recording and return events."""
        with self._lock:
            if self._state == RecorderState.STOPPED:
                return self._events

            self._flush_text()  # Flush remaining text

            self._state = RecorderState.STOPPED
            if self._mouse_listener:
                self._mouse_listener.stop()
            if self._key_listener:
                self._key_listener.stop()

            logger.info(f"Recorder stopped. Captured {len(self._events)} events.")
            return list(self._events)

    def pause(self):
        if self._state == RecorderState.RECORDING:
            self._state = RecorderState.PAUSED
            logger.info("Recorder paused.")

    def resume(self):
        if self._state == RecorderState.PAUSED:
            self._state = RecorderState.RECORDING
            logger.info("Recorder resumed.")

    def panic_clear(self):
        """Clear last 30s of events (Panic Button)."""
        with self._lock:
            cutoff = time.time() - 30
            self._events = [e for e in self._events if e.timestamp < cutoff]
            logger.warning("PANIC: Cleared last 30s of buffer.")

    def _flush_text(self):
        """Convert buffered key presses into a single TypeText event."""
        if self._current_text:
            text = "".join(self._current_text)
            self._add_event("type_text", {"text": text})
            self._current_text = []

    def _add_event(self, etype: str, data: dict):
        if self._state != RecorderState.RECORDING:
            return

        event = InputEvent(etype, data)
        self._events.append(event)
        if self._on_event:
            self._on_event(event)

    # --- Callbacks ---

    def _check_sensitive(self) -> bool:
        """Check if current context is sensitive (e.g. password field)."""
        if self._check_privacy:
            return self._check_privacy()
        return False

    def _on_click(self, x, y, button, pressed):
        if not pressed:  # Release event (Capture complete click)
            self._flush_text()  # Click ends typing

            # Privacy check for mouse? Usually less critical, but good to know
            is_sensitive = self._check_sensitive()

            self._add_event(
                "click",
                {"x": x, "y": y, "button": str(button), "sensitive": is_sensitive},
            )

    def _on_scroll(self, x, y, dx, dy):
        # Ignore scroll for now per plan, or record specific scroll
        pass

    def _on_key_press(self, key):
        # Hotkeys check logic could go here or upstream
        # Pynput GlobalHotkeys is better for control, but we monitor stream

        # Debouncing / Text Aggregation
        try:
            char = key.char
            if char:
                if self._check_sensitive():
                    # REDACTED: Do not record char
                    # Optionally record a "redacted_input" event once
                    pass
                else:
                    self._current_text.append(char)
                    self._last_key_time = time.time()
        except AttributeError:
            # Special key
            if self._current_text:
                self._flush_text()  # Flush before special key

            key_name = str(key).replace("Key.", "")
            if key_name in ["enter", "tab", "esc", "backspace"]:
                self._add_event("press_key", {"key": key_name})

    def _on_key_release(self, key):
        pass
