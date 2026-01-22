"""
Audio Recorder - Robust microphone handling with structured errors.

Features:
- Device validation before recording
- Graceful error handling (DEVICE_NOT_FOUND, DEVICE_BUSY, etc.)
- Protocol-agnostic recording interface
"""

import logging
import time
import numpy as np
from enum import Enum
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# Lazy/Safe import
try:
    import sounddevice as sd
except (ImportError, OSError):
    sd = None
    logger.warning("[AudioRecorder] sounddevice not available")

class AudioError(Enum):
    """Structured audio error types."""
    DEVICE_NOT_FOUND = "device_not_found"
    DEVICE_BUSY = "device_busy"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN = "unknown"

class AudioRecorder:
    """
    Handles audio recording with device validation and error mapping.
    """
    
    def __init__(self):
        self._sd = sd
    
    def _check_dependencies(self):
        """Deprecated: dependencies checked at module level."""
        pass
            
    def check_availability(self) -> Tuple[bool, Optional[str]]:
        """
        Check if microphone is available.
        Returns: (available, error_code)
        """
        if not self._sd:
            return False, AudioError.DEVICE_NOT_FOUND.value
            
        try:
            # Query devices to check if any input device exists
            devices = self._sd.query_devices()
            input_devices = [d for d in devices if d['max_input_channels'] > 0]
            
            if not input_devices:
                return False, AudioError.DEVICE_NOT_FOUND.value
                
            # Try to query default input device specifically
            try:
                self._sd.query_devices(kind='input')
            except Exception as e:
                if "Error opening" in str(e) or "Unanticipated host error" in str(e):
                    return False, AudioError.DEVICE_BUSY.value
                return False, AudioError.UNKNOWN.value
                
            return True, None
            
        except Exception as e:
            logger.error(f"[AudioRecorder] Availability check failed: {e}")
            return False, AudioError.UNKNOWN.value

    def record(self, duration: int, samplerate: int = 16000) -> Tuple[Optional[np.ndarray], Optional[Dict[str, Any]]]:
        """
        Record audio for specified duration.
        
        Returns: 
            (audio_data, error_dict)
            audio_data is numpy array or None on error
            error_dict contains {code, message} or None on success
        """
        if not self._sd:
            return None, {
                "code": AudioError.DEVICE_NOT_FOUND.value,
                "message": "Audio library not installed"
            }
            
        # Pre-flight check
        available, error_code = self.check_availability()
        if not available:
            return None, {
                "code": error_code,
                "message": "Microphone not available"
            }
            
        try:
            logger.info(f"[AudioRecorder] Recording for {duration}s...")
            recording = self._sd.rec(
                int(duration * samplerate),
                samplerate=samplerate,
                channels=1,
                dtype='float32'
            )
            self._sd.wait()
            return recording.flatten(), None
            
        except Exception as e:
            logger.error(f"[AudioRecorder] Recording failed: {e}")
            error_msg = str(e).lower()
            
            code = AudioError.UNKNOWN.value
            if "device" in error_msg and "found" in error_msg:
                code = AudioError.DEVICE_NOT_FOUND.value
            elif "busy" in error_msg or "opening" in error_msg:
                code = AudioError.DEVICE_BUSY.value
            elif "permission" in error_msg or "access" in error_msg:
                code = AudioError.PERMISSION_DENIED.value
                
            return None, {
                "code": code,
                "message": str(e)
            }
