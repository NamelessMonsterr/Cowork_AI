"""
High-Performance Screen Capture.

Provides:
- DXcam backend for high-FPS capture (240Hz+)
- Fallback to mss for compatibility
- Frame rate limiting
"""

import time
from typing import Optional, Tuple
from dataclasses import dataclass

try:
    import dxcam
    HAS_DXCAM = True
except ImportError:
    HAS_DXCAM = False

try:
    import mss
    import mss.tools
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

import numpy as np
from PIL import Image
import io
import base64


@dataclass
class CaptureConfig:
    """Screen capture configuration."""
    target_fps: int = 60
    use_dxcam: bool = True  # Prefer DXcam if available
    monitor: int = 0  # Primary monitor
    region: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h


class ScreenCapture:
    """
    High-performance screen capture.
    
    Uses DXcam for high FPS (240Hz+) when available,
    falls back to mss for compatibility.
    """
    
    def __init__(self, config: Optional[CaptureConfig] = None):
        self._config = config or CaptureConfig()
        self._camera = None
        self._mss = None
        self._backend = "none"
        self._last_capture_time = 0.0
        self._min_interval = 1.0 / self._config.target_fps
        
        self._initialize()
    
    def _initialize(self):
        """Initialize capture backend."""
        if self._config.use_dxcam and HAS_DXCAM:
            try:
                self._camera = dxcam.create(
                    output_idx=self._config.monitor,
                    output_color="RGB",
                )
                self._backend = "dxcam"
                print(f"Capture: Using DXcam (target: {self._config.target_fps}fps)")
                return
            except Exception as e:
                print(f"Capture: DXcam init failed: {e}")
        
        if HAS_MSS:
            self._mss = mss.mss()
            self._backend = "mss"
            print("Capture: Using mss (fallback)")
        else:
            print("Capture: No backend available!")
    
    @property
    def backend(self) -> str:
        return self._backend
    
    @property
    def is_available(self) -> bool:
        return self._backend != "none"
    
    def capture(self, as_base64: bool = False) -> Optional[bytes]:
        """
        Capture current screen.
        
        Returns raw bytes or base64 encoded PNG.
        """
        # Rate limiting
        now = time.perf_counter()
        if now - self._last_capture_time < self._min_interval:
            time.sleep(self._min_interval - (now - self._last_capture_time))
        self._last_capture_time = time.perf_counter()
        
        frame = None
        
        if self._backend == "dxcam" and self._camera:
            frame = self._dxcam_capture()
        elif self._backend == "mss" and self._mss:
            frame = self._mss_capture()
        
        if frame is None:
            return None
        
        # Convert to PNG bytes
        img = Image.fromarray(frame)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        png_bytes = buffer.getvalue()
        
        if as_base64:
            return base64.b64encode(png_bytes).decode("utf-8")
        return png_bytes
    
    def _dxcam_capture(self) -> Optional[np.ndarray]:
        """Capture using DXcam."""
        try:
            if self._config.region:
                return self._camera.grab(region=self._config.region)
            return self._camera.grab()
        except Exception:
            return None
    
    def _mss_capture(self) -> Optional[np.ndarray]:
        """Capture using mss."""
        try:
            monitor = self._mss.monitors[self._config.monitor + 1]  # mss uses 1-indexed
            
            if self._config.region:
                x, y, w, h = self._config.region
                monitor = {"left": x, "top": y, "width": w, "height": h}
            
            screenshot = self._mss.grab(monitor)
            # mss returns BGRA, convert to RGB
            frame = np.array(screenshot)
            return frame[:, :, :3][:, :, ::-1]  # BGRA -> RGB
        except Exception:
            return None
    
    def start_stream(self, fps: int = 30):
        """Start continuous capture stream (DXcam only)."""
        if self._backend == "dxcam" and self._camera:
            self._camera.start(target_fps=fps)
    
    def stop_stream(self):
        """Stop capture stream."""
        if self._backend == "dxcam" and self._camera:
            self._camera.stop()
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get latest frame from stream (DXcam only)."""
        if self._backend == "dxcam" and self._camera:
            return self._camera.get_latest_frame()
        return None
    
    def get_dimensions(self) -> Tuple[int, int]:
        """Get screen dimensions."""
        if self._backend == "mss" and self._mss:
            monitor = self._mss.monitors[self._config.monitor + 1]
            return monitor["width"], monitor["height"]
        elif self._backend == "dxcam" and self._camera:
            # DXcam doesn't have direct dimension access, use mss fallback
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                return monitor["width"], monitor["height"]
        return 1920, 1080  # Default fallback
    
    def close(self):
        """Clean up resources."""
        if self._camera:
            try:
                self._camera.stop()
            except:
                pass
        if self._mss:
            self._mss.close()


# ==================== Global Instance ====================

_global_capture: Optional[ScreenCapture] = None


def get_capture() -> ScreenCapture:
    """Get or create global capture instance."""
    global _global_capture
    if _global_capture is None:
        _global_capture = ScreenCapture()
    return _global_capture
