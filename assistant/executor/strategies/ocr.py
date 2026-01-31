"""OCR helper for text detection."""

import asyncio
from typing import Optional

try:
    import screen_ocr

    HAS_OCR = True
except ImportError:
    HAS_OCR = False

try:
    from PIL import Image
    import io
except ImportError:
    pass


class OCRBackend:
    """Wrapper for screen_ocr with WinRT backend."""

    def __init__(self):
        self._reader = None
        self._loop = None
        if HAS_OCR:
            try:
                # specific import to check for WinRT support
                from screen_ocr import Reader, WinRtBackend

                backend = WinRtBackend()
                self._reader = Reader(backend)
                print("OCR: Initialized WinRT backend")
            except (ImportError, ValueError) as e:
                print(
                    f"OCR: WinRT initialization failed ({e}), falling back to default"
                )
                try:
                    self._reader = screen_ocr.Reader.create_quality_reader()
                except Exception as e2:
                    print(f"OCR: Default reader failed: {e2}")

    def read_text(
        self, image_bytes: bytes, region: Optional[tuple[int, int, int, int]] = None
    ) -> str:
        """
        Read text from image bytes using WinRT OCR.

        Args:
            image_bytes: PNG/JPEG bytes
            region: Optional crop region (x1, y1, x2, y2)

        Returns:
            Extracted text
        """
        if not HAS_OCR:
            return ""

        try:
            # Create PIL image
            img = Image.open(io.BytesIO(image_bytes))

            # Crop if region specified
            if region:
                img = img.crop(region)

            # screen_ocr usually takes a ScreenContents or similar,
            # but wrapping it allows us to just pass the image.
            # However, screen_ocr is designed to take Screenshots.
            # Let's adapt:

            # Native screen_ocr usage is async and geared towards full screen
            # We will use the underlying library (winocr) logic via run_in_executor
            # Or simpler: use screen_ocr's image method if available,
            # otherwise implement direct WinRT or EasyOCR fallback.

            # For this Phase 2 implementation, we'll use a simplified synchronous wrapper
            # that re-uses the event loop if possible.

            result = self._run_async(self._reader.read_image(img))

            return result.as_string()

        except Exception as e:
            print(f"OCR Error: {e}")
            return ""

    def _run_async(self, coro):
        """Run async code synchronously."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # We are already in a loop, this is tricky.
            # For now, we assume this is called from thread pool if in async app
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()
        else:
            return loop.run_until_complete(coro)


# Global instance
_ocr_instance = None


def get_ocr_engine() -> OCRBackend:
    """Get global OCR engine instance."""
    global _ocr_instance
    if _ocr_instance is None:
        _ocr_instance = OCRBackend()
    return _ocr_instance
