"""
Voice API Routes - V21 Voice Real Mode.

Endpoints:
- GET /voice/devices - List available microphone devices
- GET /voice/health - STT engine health status
- POST /voice/listen - Record and transcribe voice
"""

import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException

logger = logging.getLogger("VoiceRoutes")

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/devices")
async def list_audio_devices():
    """
    List available audio input devices.
    
    Returns:
        devices: List of {id, name, is_default}
        error: Optional error message if audio unavailable
    """
    try:
        import sounddevice as sd
        
        devices = sd.query_devices()
        input_devices = []
        default_device = sd.default.device[0]  # Input device index
        
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                input_devices.append({
                    "id": str(i),
                    "name": dev['name'],
                    "is_default": (i == default_device),
                    "channels": dev['max_input_channels'],
                    "sample_rate": int(dev['default_samplerate'])
                })
        
        logger.info(f"[Voice] Found {len(input_devices)} input devices")
        return {
            "success": True,
            "devices": input_devices,
            "default_device": str(default_device) if default_device is not None else None
        }
        
    except ImportError:
        logger.warning("[Voice] sounddevice not installed")
        return {
            "success": False,
            "devices": [],
            "error": "Audio library (sounddevice) not available"
        }
    except Exception as e:
        logger.error(f"[Voice] Device enumeration failed: {e}")
        return {
            "success": False,
            "devices": [],
            "error": str(e)
        }


@router.post("/test")
async def test_stt(request: Request, seconds: int = 3):
    """
    Quick STT test - record and transcribe.
    Useful for verifying STT configuration.
    
    Returns:
        engine: STT engine used
        transcript: Recognized text
        duration_ms: Total processing time in milliseconds
        error: Structured error if failed
    """
    import time
    start = time.time()
    
    # PIPELINE FIX: Access wired global state
    state = request.app.state.state
    
    try:
        text = await state.stt.listen(duration=seconds)
        engine = state.stt.engine_name
        duration_ms = int((time.time() - start) * 1000)
        
        return {
            "success": True,
            "engine": engine,
            "transcript": text,
            "duration_ms": duration_ms
        }
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        logger.error(f"[Voice] Test failed: {e}")
        
        # Check for structured STTError
        error_code = "unknown_error"
        error_msg = str(e)
        
        if hasattr(e, "code"):  # STTError has code attribute
            error_code = e.code
            error_msg = e.message
            
        return {
            "success": False,
            "error": {
                "code": error_code,
                "message": error_msg
            },
            "duration_ms": duration_ms
        }
