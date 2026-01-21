from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/voice/stream")
async def voice_stream(
    websocket: WebSocket, 
    session_id: str = Query(None)  # Get session from URL param
):
    """Secure WebSocket voice stream with session verification"""
    
    # CRITICAL: Verify session from query param
    from assistant.main import state
    
    if not session_id or not state.session_auth.check():
        logger.warning(f"WebSocket rejected: Invalid session {session_id}")
        await websocket.close(code=1008, reason="Invalid session")
        return
    
    await websocket.accept()
    logger.info(f"✅ Voice WebSocket connected (session: {session_id[:8]}...)")
    
    try:
        while True:
            data = await websocket.receive_bytes()
            logger.debug(f"Received audio chunk: {len(data)} bytes")
            
            # TODO: Integrate with actual STT service
            await websocket.send_json({
                "type": "transcript",
                "text": "Audio received (STT not yet integrated)",
                "timestamp": datetime.utcnow().isoformat()
            })
            
    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")
    except Exception as e:
        logger.error(f"Voice Error: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        await websocket.close()
