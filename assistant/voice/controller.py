"""
Voice Controller - Manages STT/TTS integration.

Provides:
- Push-to-talk hotkey
- State machine for voice flow
- Event coordination
"""

import threading
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

from .stt import WhisperSTT, STTState, TranscriptionResult
from .tts import EdgeTTS, TTSState


class VoiceState(str, Enum):
    """Voice controller state."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


@dataclass
class VoiceConfig:
    """Voice controller configuration."""
    push_to_talk_key: str = "ctrl+space"
    whisper_model: str = "base"
    default_voice: str = "en-US-AriaNeural"
    narrate_steps: bool = True
    narrate_takeover: bool = True


class VoiceController:
    """
    Voice Controller - Coordinates STT and TTS.
    
    Features:
    - Push-to-talk with configurable hotkey
    - Automatic TTS narration of events
    - Interrupt keyword handling
    - State machine for voice flow
    """
    
    def __init__(
        self,
        config: Optional[VoiceConfig] = None,
        on_command: Optional[Callable[[str], None]] = None,
        on_interrupt: Optional[Callable[[str], None]] = None,
        on_state_change: Optional[Callable[[VoiceState], None]] = None,
    ):
        """
        Initialize voice controller.
        
        Args:
            config: Voice configuration
            on_command: Callback when voice command recognized
            on_interrupt: Callback when interrupt keyword detected
            on_state_change: Callback when state changes
        """
        self._config = config or VoiceConfig()
        self._on_command = on_command
        self._on_interrupt = on_interrupt
        self._on_state_change = on_state_change
        
        self._state = VoiceState.IDLE
        self._hotkey_registered = False
        
        # Initialize STT
        self._stt = WhisperSTT(
            model_size=self._config.whisper_model,
            on_transcription=self._handle_transcription,
            on_interrupt=self._handle_interrupt,
        )
        
        # Initialize TTS
        self._tts = EdgeTTS(
            default_voice=self._config.default_voice,
            on_speaking_start=self._on_speaking_start,
            on_speaking_end=self._on_speaking_end,
        )
    
    @property
    def state(self) -> VoiceState:
        return self._state
    
    @property
    def is_available(self) -> bool:
        return self._stt.is_available or self._tts.is_available
    
    @property
    def stt(self) -> WhisperSTT:
        return self._stt
    
    @property
    def tts(self) -> EdgeTTS:
        return self._tts
    
    def _set_state(self, state: VoiceState):
        """Set state and notify callback."""
        old_state = self._state
        self._state = state
        
        if old_state != state and self._on_state_change:
            self._on_state_change(state)
    
    def start(self):
        """Start voice controller and register hotkey."""
        if HAS_KEYBOARD and not self._hotkey_registered:
            try:
                keyboard.add_hotkey(
                    self._config.push_to_talk_key,
                    self._toggle_listening,
                    suppress=True,
                )
                self._hotkey_registered = True
                print(f"Voice: Registered hotkey {self._config.push_to_talk_key}")
            except Exception as e:
                print(f"Voice: Failed to register hotkey: {e}")
    
    def stop(self):
        """Stop voice controller and unregister hotkey."""
        if HAS_KEYBOARD and self._hotkey_registered:
            try:
                keyboard.remove_hotkey(self._config.push_to_talk_key)
                self._hotkey_registered = False
            except:
                pass
        
        self._tts.stop()
        self._set_state(VoiceState.IDLE)
    
    def _toggle_listening(self):
        """Toggle push-to-talk."""
        if self._state == VoiceState.IDLE:
            self.start_listening()
        elif self._state == VoiceState.LISTENING:
            self.stop_listening()
    
    def start_listening(self):
        """Start listening for voice input."""
        if self._state != VoiceState.IDLE:
            return
        
        # Stop any ongoing speech
        self._tts.stop()
        
        self._set_state(VoiceState.LISTENING)
        self._stt.start_listening()
    
    def stop_listening(self) -> Optional[TranscriptionResult]:
        """Stop listening and process speech."""
        if self._state != VoiceState.LISTENING:
            return None
        
        self._set_state(VoiceState.PROCESSING)
        result = self._stt.stop_listening()
        self._set_state(VoiceState.IDLE)
        
        return result
    
    def speak(self, text: str, blocking: bool = False):
        """Speak text using TTS."""
        self._tts.speak(text, blocking=blocking)
    
    def narrate_event(self, event_type: str, details: str = ""):
        """Narrate an event if configured."""
        should_narrate = (
            (event_type in ["task_start", "task_complete", "error"] and self._config.narrate_steps) or
            (event_type == "takeover_required" and self._config.narrate_takeover)
        )
        
        if should_narrate:
            self._tts.narrate_event(event_type, details)
    
    def _handle_transcription(self, result: TranscriptionResult):
        """Handle transcription result."""
        if result.text and self._on_command:
            self._on_command(result.text)
    
    def _handle_interrupt(self, keyword: str):
        """Handle interrupt keyword."""
        print(f"Voice: Interrupt detected: {keyword}")
        if self._on_interrupt:
            self._on_interrupt(keyword)
    
    def _on_speaking_start(self):
        """Handle TTS speaking start."""
        self._set_state(VoiceState.SPEAKING)
    
    def _on_speaking_end(self):
        """Handle TTS speaking end."""
        if self._state == VoiceState.SPEAKING:
            self._set_state(VoiceState.IDLE)
    
    def get_status(self) -> dict:
        """Get current voice status."""
        return {
            "state": self._state.value,
            "stt_state": self._stt.state.value,
            "tts_state": self._tts.state.value,
            "stt_available": self._stt.is_available,
            "tts_available": self._tts.is_available,
            "hotkey_registered": self._hotkey_registered,
            "push_to_talk_key": self._config.push_to_talk_key,
        }
