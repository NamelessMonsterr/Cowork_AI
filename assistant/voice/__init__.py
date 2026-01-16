"""
Voice Module - STT, TTS, and Voice Controller.

Provides:
- WhisperSTT: Local speech-to-text with faster-whisper
- EdgeTTS: High-quality text-to-speech with edge-tts
- VoiceController: Coordinates STT/TTS with push-to-talk
"""

from .stt import (
    WhisperSTT,
    STTState,
    TranscriptionResult,
    HAS_WHISPER,
    HAS_AUDIO,
)

from .tts import (
    EdgeTTS,
    TTSState,
    SpeechRequest,
    HAS_EDGE_TTS,
)

from .controller import (
    VoiceController,
    VoiceState,
    VoiceConfig,
)

__all__ = [
    # STT
    "WhisperSTT",
    "STTState", 
    "TranscriptionResult",
    "HAS_WHISPER",
    "HAS_AUDIO",
    
    # TTS
    "EdgeTTS",
    "TTSState",
    "SpeechRequest",
    "HAS_EDGE_TTS",
    
    # Controller
    "VoiceController",
    "VoiceState",
    "VoiceConfig",
]
