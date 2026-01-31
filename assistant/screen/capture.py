"""
Screen Capture Module using DXCam (Primary) and MSS (Fallback).
Supports multi-monitor, ROI, and dynamic FPS control (W7.1).
"""

import base64
import io
import logging
import platform
import threading

from PIL import Image

# dxcam import guarded
HAS_DXCAM = False
try:
    if platform.system() == "Windows":
        import dxcam

        HAS_DXCAM = True
except ImportError:
    pass
except Exception:
    pass

import mss

logger = logging.getLogger("ScreenCapture")


class ScreenCapture:
    def __init__(self, preferred_fps: float = 2.0, monitor_idx: int = 0):
        self._lock = threading.Lock()
        self._target_fps = float(preferred_fps)
        self._interval = 1.0 / max(0.001, self._target_fps)
        self._monitor_idx = monitor_idx

        self._dx_cam = None
        if HAS_DXCAM:
            try:
                # Output as BGRA is faster/native for DXCam usually
                self._dx_cam = dxcam.create(device_idx=monitor_idx, output_color="BGRA")
                logger.info(f"DXCam initialized on monitor {monitor_idx}")
            except Exception as e:
                logger.warning(f"DXCam init failed: {e}")
                self._dx_cam = None

        self._mss = mss.mss()

    def set_target_fps(self, fps: float):
        """Set the target capture FPS."""
        with self._lock:
            self._target_fps = max(0.1, float(fps))
            self._interval = 1.0 / self._target_fps
            logger.debug(f"Target FPS set to {self._target_fps}")

    def _capture_with_dx(self, region: tuple | None = None):
        # dxcam capture call (fast) - returns a numpy image
        if not self._dx_cam:
            raise RuntimeError("DXCam not available")

        # Region for dxcam is (left, top, right, bottom)
        if region:
            left, top, right, bottom = region
            # Ensure ints
            region_rect = (int(left), int(top), int(right), int(bottom))
            img = self._dx_cam.grab(region=region_rect)
        else:
            img = self._dx_cam.grab()

        if img is None:
            return None

        return Image.fromarray(img)

    def _capture_with_mss(self, region: tuple | None = None):
        with self._lock:  # MSS is not always thread safe depending on OS
            # monitor[0] is all, monitor[1] is primary.
            # logic: map monitor_idx 0 -> monitor 1 (primary)
            monitors = self._mss.monitors
            mon_idx = min(self._monitor_idx + 1, len(monitors) - 1)
            monitor = monitors[mon_idx]

            if region:
                left, top, right, bottom = region
                # MSS wants: {'top': t, 'left': l, 'width': w, 'height': h}
                # And coordinates must be relative to the monitor or absolute?
                # Usually MSS handles absolute if monitor is not specified
                # OR we specify the dict relative to virtual screen.
                # Simplest: Just specify the rect properties.
                capture_req = {
                    "left": int(left),
                    "top": int(top),
                    "width": int(right - left),
                    "height": int(bottom - top),
                }
            else:
                capture_req = monitor

            sct_img = self._mss.grab(capture_req)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return img

    def capture(self, region: tuple | None = None) -> Image.Image:
        """Capture screen content as PIL Image."""
        # Try DX first, fallback to MSS.
        if self._dx_cam:
            try:
                img = self._capture_with_dx(region)
                if img:
                    return img
            except Exception:
                # fallback
                pass
        return self._capture_with_mss(region)

    def capture_base64(self, region: tuple | None = None) -> str:
        """Capture and return as base64 string."""
        img = self.capture(region)
        if not img:
            return ""
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("ascii")

    def release(self):
        if self._dx_cam:
            pass
        self._mss.close()
