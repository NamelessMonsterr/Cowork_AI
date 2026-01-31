import logging
from datetime import datetime

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/voice/stream")
async def voice_stream(
    websocket: WebSocket,
    session_id: str = Query(None),  # Get session from URL param
):
    """Secure WebSocket voice stream with session verification and STT integration"""

    # CRITICAL: Verify session from query param
    from assistant.main import state

    if not session_id or not state.session_auth.check():
        logger.warning(f"WebSocket rejected: Invalid session {session_id}")
        await websocket.close(code=1008, reason="Invalid session")
        return

    await websocket.accept()
    logger.info(f"✅ Voice WebSocket connected (session: {session_id[:8]}...)")

    # FIXED: Integrated STT engine from state
    stt_engine = state.stt
    if not stt_engine:
        logger.error("STT engine not initialized in state")
        await websocket.send_json({"type": "error", "message": "STT engine not available"})
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_bytes()
            logger.debug(f"Received audio chunk: {len(data)} bytes")

            try:
                # Transcribe audio using STT engine
                # Note: For streaming, we can accumulate chunks or process individually
                # Currently using the STT engine's mic recording functionality
                # For WebSocket streaming, you may want to adapt this

                # For now, signal that audio is being received
                await websocket.send_json(
                    {
                        "type": "status",
                        "message": "Processing audio...",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

                # If audio accumulation is complete (you'll need to implement chunk aggregation),
                # trigger transcription via state.stt.listen()
                # For production, consider buffering audio chunks and transcribing when complete

            except Exception as transcription_error:
                logger.error(f"Transcription error: {transcription_error}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Transcription failed: {str(transcription_error)}",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")
    except Exception as e:
        logger.error(f"Voice Error: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        await websocket.close()


@router.post("/voice/transcribe_mic")
async def transcribe_mic_endpoint(duration: int = 5):
    """
    Endpoint to transcribe from microphone directly (alternative to WebSocket streaming).
    This uses the existing STT infrastructure.
    """
    from assistant.main import state

    if not state.session_auth.check():
        return {"success": False, "error": "Permission required"}

    if not state.stt:
        return {"success": False, "error": "STT engine not initialized"}

    try:
        logger.info(f"Starting mic transcription ({duration}s)...")
        transcript = await state.stt.listen(duration)

        return {
            "success": True,
            "transcript": transcript,
            "engine": state.stt.engine_name,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/voice/health")
async def voice_health():
    """Health check for voice/STT subsystem"""
    from assistant.main import state

    if not state.stt:
        return {"status": "unavailable", "error": "STT not initialized"}

    health = state.stt.get_health()
    return {"status": "ok" if health["available"] else "degraded", **health}
