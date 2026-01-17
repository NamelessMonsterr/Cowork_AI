"""
Settings API Routes.
Manages application configuration and dynamic reloading.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from assistant.config.settings import get_settings, VoiceSettings

logger = logging.getLogger("SettingsAPI")

router = APIRouter(prefix="/settings", tags=["settings"])

class SettingsUpdate(BaseModel):
    voice: Optional[VoiceSettings] = None

@router.get("")
async def get_current_settings():
    """Get current application settings."""
    return get_settings()

@router.put("")
async def update_settings(update: SettingsUpdate, request: Request):
    """
    Update settings and reload affected components.
    """
    settings = get_settings()
    
    # Update Voice Settings
    if update.voice:
        logger.info(f"Updating Voice Settings: {update.voice}")
        settings.voice = update.voice
        settings.save()
        
        # Reload STT Engine if changed
        if hasattr(request.app.state, 'stt'):
            from assistant.voice.stt import STT
            
            logger.info("Reloading STT Engine...")
            try:
                # Re-create STT instance with new settings
                # Note: STTEngineFactory logic handles preference priority
                mock_mode = settings.voice.mock_stt or (settings.voice.engine_preference == 'mock')
                
                new_stt = STT(
                    prefer_mock=mock_mode,
                    openai_api_key=settings.voice.openai_api_key
                )
                
                # Update request state
                request.app.state.stt = new_stt
                
                # CRITICAL: Update Global State in main.py because voice_listen uses it directly
                try:
                    from assistant.main import state as global_state
                    global_state.stt = new_stt
                    logger.info("Global State STT updated.")
                except ImportError:
                    logger.warning("Could not import global state to update STT.")

                logger.info(f"STT Reloaded. New Engine: {new_stt.engine_name}")
                
            except Exception as e:
                logger.error(f"Failed to reload STT: {e}")
                
    return {"status": "updated", "settings": settings}
