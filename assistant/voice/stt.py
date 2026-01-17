"""
Speech-to-Text Module - Protocol-based Engine Abstraction.

Supports multiple STT backends with automatic fallback:
1. FasterWhisperSTT (local, preferred)
2. OpenAIWhisperSTT (API, fallback)
3. MockSTT (dev mode only)
"""

import logging
import os
import time
import asyncio
from typing import Protocol, Optional, runtime_checkable
from abc import ABC, abstractmethod

logger = logging.getLogger("STT")


# ==================== Protocol Definition ====================

@runtime_checkable
class STTEngine(Protocol):
    """Protocol for STT engine implementations."""
    
    @property
    def name(self) -> str:
        """Engine name for logging/health."""
        ...
    
    def is_available(self) -> bool:
        """Check if engine is ready to use."""
        ...
    
    async def transcribe_mic(self, seconds: int = 5) -> str:
        """Record from mic and transcribe. Returns transcript or empty string."""
        ...


# ==================== Engine Implementations ====================

class FasterWhisperSTT:
    """Primary STT engine using local faster-whisper model."""
    
    _model = None
    _error: Optional[str] = None
    _has_audio = False
    
    def __init__(self, model_size: str = "tiny", device: str = "cpu"):
        self._model_size = model_size
        self._device = device
        self._init_dependencies()
    
    def _init_dependencies(self):
        """Initialize audio and whisper dependencies."""
        # Audio dependencies
        try:
            import numpy as np
            import sounddevice as sd
            self._np = np
            self._sd = sd
            self._has_audio = True
        except ImportError as e:
            self._error = f"Audio deps missing: {e}"
            self._has_audio = False
            logger.warning(f"[FasterWhisper] {self._error}")
            return
        
        # Whisper model
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self._model_size, device=self._device, compute_type="int8")
            logger.info(f"[FasterWhisper] Model '{self._model_size}' loaded on {self._device}")
        except Exception as e:
            self._error = f"faster-whisper load failed: {e}"
            logger.warning(f"[FasterWhisper] {self._error}")
    
    @property
    def name(self) -> str:
        return "faster-whisper"
    
    def is_available(self) -> bool:
        return self._model is not None and self._has_audio
    
    def get_error(self) -> Optional[str]:
        return self._error
    
    async def transcribe_mic(self, seconds: int = 5) -> str:
        """Record from microphone and transcribe."""
        if not self.is_available():
            raise RuntimeError(f"FasterWhisperSTT not available: {self._error}")
        
        return await asyncio.to_thread(self._transcribe_sync, seconds)
    
    def _transcribe_sync(self, seconds: int) -> str:
        """Synchronous recording and transcription."""
        logger.info(f"[FasterWhisper] Recording for {seconds}s...")
        
        try:
            samplerate = 16000
            recording = self._sd.rec(int(seconds * samplerate), samplerate=samplerate, channels=1, dtype='float32')
            self._sd.wait()
            
            audio_data = recording.flatten()
            segments, info = self._model.transcribe(audio_data, beam_size=5)
            text = " ".join([segment.text for segment in segments]).strip()
            
            logger.info(f"[FasterWhisper] Transcribed: '{text}'")
            return text
            
        except Exception as e:
            logger.error(f"[FasterWhisper] Transcription error: {e}")
            raise


class OpenAIWhisperSTT:
    """Fallback STT engine using OpenAI Whisper API."""
    
    _client = None
    _error: Optional[str] = None
    _has_audio = False
    
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._init_dependencies()
    
    def _init_dependencies(self):
        """Initialize OpenAI client and audio deps."""
        if not self._api_key:
            self._error = "No OpenAI API key configured"
            logger.warning(f"[OpenAIWhisper] {self._error}")
            return
        
        # Audio dependencies
        try:
            import numpy as np
            import sounddevice as sd
            import wave
            import tempfile
            self._np = np
            self._sd = sd
            self._wave = wave
            self._tempfile = tempfile
            self._has_audio = True
        except ImportError as e:
            self._error = f"Audio deps missing: {e}"
            self._has_audio = False
            logger.warning(f"[OpenAIWhisper] {self._error}")
            return
        
        # OpenAI client
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
            logger.info("[OpenAIWhisper] Client initialized")
        except Exception as e:
            self._error = f"OpenAI client init failed: {e}"
            logger.warning(f"[OpenAIWhisper] {self._error}")
    
    @property
    def name(self) -> str:
        return "openai-whisper"
    
    def is_available(self) -> bool:
        return self._client is not None and self._has_audio
    
    def get_error(self) -> Optional[str]:
        return self._error
    
    async def transcribe_mic(self, seconds: int = 5) -> str:
        """Record from microphone and transcribe via API."""
        if not self.is_available():
            raise RuntimeError(f"OpenAIWhisperSTT not available: {self._error}")
        
        return await asyncio.to_thread(self._transcribe_sync, seconds)
    
    def _transcribe_sync(self, seconds: int) -> str:
        """Synchronous recording and API transcription."""
        logger.info(f"[OpenAIWhisper] Recording for {seconds}s...")
        
        try:
            samplerate = 16000
            recording = self._sd.rec(int(seconds * samplerate), samplerate=samplerate, channels=1, dtype='int16')
            self._sd.wait()
            
            # Save to temp WAV file
            with self._tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
                with self._wave.open(f, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)  # int16 = 2 bytes
                    wf.setframerate(samplerate)
                    wf.writeframes(recording.tobytes())
            
            # Send to API
            with open(temp_path, 'rb') as audio_file:
                response = self._client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            
            # Cleanup
            os.unlink(temp_path)
            
            text = response.text.strip()
            logger.info(f"[OpenAIWhisper] Transcribed: '{text}'")
            return text
            
        except Exception as e:
            logger.error(f"[OpenAIWhisper] Transcription error: {e}")
            raise


class MockSTT:
    """Mock STT engine for development/testing."""
    
    MOCK_PHRASES = [
        "Open Notepad and type Hello World",
        "Open Calculator",
        "Open File Explorer",
    ]
    _call_count = 0
    
    @property
    def name(self) -> str:
        return "mock"
    
    def is_available(self) -> bool:
        return True  # Always available
    
    def get_error(self) -> Optional[str]:
        return None
    
    async def transcribe_mic(self, seconds: int = 5) -> str:
        """Return mock transcript with simulated delay."""
        logger.info(f"[MockSTT] Simulating {seconds}s recording...")
        await asyncio.sleep(min(seconds, 2))  # Cap delay at 2s
        
        phrase = self.MOCK_PHRASES[self._call_count % len(self.MOCK_PHRASES)]
        MockSTT._call_count += 1
        
        logger.info(f"[MockSTT] Returning: '{phrase}'")
        return phrase


# ==================== Engine Factory ====================

class STTEngineFactory:
    """
    Factory for selecting the best available STT engine.
    
    Priority:
    1. FasterWhisperSTT (local, fast)
    2. OpenAIWhisperSTT (API, reliable)
    3. MockSTT (dev fallback)
    """
    
    def __init__(self, 
                 prefer_mock: bool = False,
                 openai_api_key: Optional[str] = None,
                 whisper_model: str = "tiny",
                 whisper_device: str = "cpu"):
        self._prefer_mock = prefer_mock
        self._openai_api_key = openai_api_key
        self._whisper_model = whisper_model
        self._whisper_device = whisper_device
        
        # Initialize engines
        self._engines = []
        self._selected_engine: Optional[STTEngine] = None
        self._init_engines()
    
    def _init_engines(self):
        """Initialize all engines and select the best one."""
        logger.info("[STT Factory] Initializing engines...")
        
        if self._prefer_mock:
            logger.info("[STT Factory] Mock mode enabled, using MockSTT")
            self._selected_engine = MockSTT()
            self._engines.append(self._selected_engine)
            return
        
        # Try FasterWhisper first
        fw = FasterWhisperSTT(model_size=self._whisper_model, device=self._whisper_device)
        self._engines.append(fw)
        if fw.is_available():
            self._selected_engine = fw
            logger.info(f"[STT Factory] Selected: {fw.name}")
            return
        
        # Try OpenAI Whisper
        oa = OpenAIWhisperSTT(api_key=self._openai_api_key)
        self._engines.append(oa)
        if oa.is_available():
            self._selected_engine = oa
            logger.info(f"[STT Factory] Selected: {oa.name}")
            return
        
        # Fallback to Mock
        logger.warning("[STT Factory] No real STT available, falling back to MockSTT")
        mock = MockSTT()
        self._engines.append(mock)
        self._selected_engine = mock
    
    def get_engine(self) -> STTEngine:
        """Get the selected STT engine."""
        return self._selected_engine
    
    def get_health(self) -> dict:
        """Get health status for /voice/health endpoint."""
        engine = self._selected_engine
        errors = []
        
        for e in self._engines:
            if hasattr(e, 'get_error') and e.get_error():
                errors.append(f"{e.name}: {e.get_error()}")
        
        return {
            "stt_engine": engine.name if engine else "none",
            "available": engine.is_available() if engine else False,
            "error": "; ".join(errors) if errors else None,
            "engines_tried": [e.name for e in self._engines]
        }


# ==================== Backwards-Compatible STT Class ====================

class STT:
    """
    Backwards-compatible STT class.
    Uses STTEngineFactory internally for engine selection.
    """
    
    def __init__(self, 
                 model_size: str = "tiny", 
                 device: str = "cpu",
                 prefer_mock: bool = False,
                 openai_api_key: Optional[str] = None):
        self._factory = STTEngineFactory(
            prefer_mock=prefer_mock,
            openai_api_key=openai_api_key,
            whisper_model=model_size,
            whisper_device=device
        )
        self._engine = self._factory.get_engine()
    
    async def listen(self, duration: int = 5) -> str:
        """
        Record and transcribe (async).
        Returns transcript or empty string on failure.
        """
        task_id = os.environ.get("CURRENT_TASK_ID", "unknown")
        
        logger.info(f"[VOICE] Listen started | task_id={task_id}")
        logger.info(f"[VOICE] Engine selected: {self._engine.name} | task_id={task_id}")
        
        try:
            text = await self._engine.transcribe_mic(duration)
            logger.info(f"[VOICE] Transcript received: '{text}' | task_id={task_id}")
            return text
        except Exception as e:
            logger.error(f"[VOICE] Transcription failed: {e} | task_id={task_id}")
            return ""
    
    def get_health(self) -> dict:
        """Get STT health status."""
        return self._factory.get_health()
    
    @property
    def engine_name(self) -> str:
        """Get current engine name."""
        return self._engine.name if self._engine else "none"
