"""
Text-to-Speech Module using Edge-TTS (Robust).
"""

import asyncio
import logging
import os
import tempfile

logger = logging.getLogger("TTS")

# Try imports
try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False
    logger.warning("edge-tts not installed. Voice will be disabled.")

try:
    from playsound import playsound
    HAS_PLAYSOUND = True
except ImportError:
    HAS_PLAYSOUND = False
    logger.warning("playsound not installed. Audio playback will be disabled.")

class TTS:
    def __init__(self, voice: str = "en-GB-RyanNeural"):
        self.voice = voice

    async def speak(self, text: str):
        """
        Synthesize text to speech and play it immediately.
        """
        logger.info(f"Speaking: {text}")
        if not text:
            return

        if not (HAS_EDGE_TTS and HAS_PLAYSOUND):
            logger.info(f"[MOCK SPEECH] >> {text}")
            return

        try:
            # Create a localized temporary file
            # edge-tts requires an output file
            
            communicate = edge_tts.Communicate(text, self.voice)
            
            # Save to a temp file
            # Using a unique name to avoid conflicts
            temp_path = os.path.join(tempfile.gettempdir(), f"cowork_speech_{os.getpid()}.mp3")
            
            await communicate.save(temp_path)
            
            # Play audio (blocking or threaded)
            await asyncio.to_thread(playsound, temp_path)
            
            # Cleanup
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.debug(f"Failed to cleanup TTS temp file: {e}")
                pass
                
        except Exception as e:
            logger.error(f"TTS Failed: {e}")
            logger.info(f"[FAILED SPEECH] >> {text}")
