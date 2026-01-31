"""
Voice API Routes - V21 Voice Real Mode.

Endpoints:
- GET /voice/devices - List available microphone devices
- GET /voice/health - STT engine health status
- POST /voice/listen - Record and transcribe voice
"""

import logging

from fastapi import APIRouter, Request

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
            if dev["max_input_channels"] > 0:
                input_devices.append(
                    {
                        "id": str(i),
                        "name": dev["name"],
                        "is_default": (i == default_device),
                        "channels": dev["max_input_channels"],
                        "sample_rate": int(dev["default_samplerate"]),
                    }
                )

        logger.info(f"[Voice] Found {len(input_devices)} input devices")
        return {
            "success": True,
            "devices": input_devices,
            "default_device": str(default_device) if default_device is not None else None,
        }

    except ImportError:
        logger.warning("[Voice] sounddevice not installed")
        return {
            "success": False,
            "devices": [],
            "error": "Audio library (sounddevice) not available",
        }
    except Exception as e:
        logger.error(f"[Voice] Device enumeration failed: {e}")
        return {"success": False, "devices": [], "error": str(e)}


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
            "duration_ms": duration_ms,
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
            "error": {"code": error_code, "message": error_msg},
            "duration_ms": duration_ms,
        }


@router.post("/execute")
async def voice_execute(request: Request, seconds: int = 5):
    """
    Record voice → Transcribe → Execute immediately.
    Production-ready with error handling.
    """
    import time

    import httpx

    start = time.time()
    state = request.app.state.state

    # Auto-grant session if needed (demo mode)
    if not state.session_auth.check():
        state.session_auth.grant(mode="session", apps={"*"}, folders={"*"})
        logger.info("Auto-granted session for voice execute")

    try:
        # 1. Record and transcribe
        logger.info(f"Recording for {seconds}s...")
        text = await state.stt.listen(duration=seconds)

        if not text:
            return {
                "success": False,
                "error": "No speech detected",
                "stage": "transcription",
                "duration_ms": int((time.time() - start) * 1000),
            }

        logger.info(f"Heard: '{text}'")

        # 2. Call the working execution endpoint
        async with httpx.AsyncClient() as client:
            exec_response = await client.post("http://127.0.0.1:8765/just_do_it", json={"task": text}, timeout=30.0)
            exec_result = exec_response.json()

        total_duration = int((time.time() - start) * 1000)

        return {
            "success": exec_result.get("success", False),
            "transcript": text,
            "execution": exec_result,
            "duration_ms": total_duration,
        }

    except Exception as e:
        logger.error(f"Voice execute failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "stage": "execution",
            "duration_ms": int((time.time() - start) * 1000),
        }
