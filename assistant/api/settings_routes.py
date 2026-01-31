"""
Settings API Routes.
Manages application configuration and dynamic reloading.
"""

import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from assistant.config.settings import VoiceSettings, get_settings
# CRITICAL SECURITY FIX: Add authentication
from assistant.auth import require_api_key

logger = logging.getLogger("SettingsAPI")

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    voice: VoiceSettings | None = None


# CRITICAL SECURITY: Authentication required for reading sensitive config
@router.get("", dependencies=[Depends(require_api_key)])
async def get_current_settings():
    """Get current application settings."""
    return get_settings()


# CRITICAL SECURITY: Authentication required for modifying config
@router.put("", dependencies=[Depends(require_api_key)])
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
        # PIPELINE FIX: Access wired global state
        if hasattr(request.app.state, "state"):
            from assistant.voice.stt import STT

            logger.info("Reloading STT Engine...")
            try:
                # Re-create STT instance with new settings
                mock_mode = settings.voice.mock_stt or (settings.voice.engine_preference == "mock")

                new_stt = STT(prefer_mock=mock_mode, openai_api_key=settings.voice.openai_api_key)

                # PIPELINE FIX: Update global state directly (now wired to app.state.state)
                state = request.app.state.state
                state.stt = new_stt
                logger.info(f"STT Reloaded. New Engine: {new_stt.engine_name}")

            except Exception as e:
                logger.error(f"Failed to reload STT: {e}")

    return {"status": "updated", "settings": settings}
