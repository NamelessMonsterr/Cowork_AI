"""
Download Watcher - Monitors file downloads and creation.

Tracks the Downloads folder (or other paths) to:
- Detect new files
- Wait for downloads to complete (size stability)
- Verify file extensions
- Handle name collisions
"""

import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class DownloadEvent:
    """Event triggered when a download activity is detected."""

    path: str
    filename: str
    size: int
    is_complete: bool
    duration_sec: float


class DownloadWatcher:
    """
    Watches directories for new files and tracks download completion.

    Usage:
        watcher = DownloadWatcher(
            paths=["C:/Users/User/Downloads"],
            on_download_complete=lambda event: print(f"Downloaded: {event.filename}")
        )
        watcher.start()

        # ... perform download action ...

        # Wait for next download
        event = watcher.wait_for_download(timeout=30)

        watcher.stop()
    """

    def __init__(
        self,
        watch_paths: list[str] = None,
        on_download_complete: Callable[[DownloadEvent], None] | None = None,
        stability_duration: float = 2.0,  # File size must be stable for 2s
        check_interval: float = 0.5,
    ):
        """
        Initialize DownloadWatcher.

        Args:
            watch_paths: List of paths to watch (default: user Downloads)
            on_download_complete: Callback when download completes
            stability_duration: Seconds file size must be stable to be "complete"
            check_interval: Polling interval
        """
        if watch_paths is None:
            # Default to Downloads folder
            watch_paths = [os.path.join(os.path.expanduser("~"), "Downloads")]

        self._watch_paths = [os.path.abspath(p) for p in watch_paths]
        self._on_complete = on_download_complete
        self._stability_duration = stability_duration
        self._check_interval = check_interval

        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

        # Track pending files: {abspath: {"start_time": t, "last_size": s, "stable_since": t}}
        self._pending_files = {}

        # Snapshots of directory state
        self._known_files = set()

        # Event for synchronous waiting
        self._wait_event = threading.Event()
        self._last_download: DownloadEvent | None = None

    def start(self) -> None:
        """Start watching."""
        with self._lock:
            if self._running:
                return

            # Take initial snapshot
            self._known_files = self._scan_files()

            self._running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop watching."""
        with self._lock:
            self._running = False

        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def wait_for_download(self, timeout: float = 30.0) -> DownloadEvent | None:
        """
        Block until a new download completes.

        Args:
            timeout: Max wait time in seconds

        Returns:
            DownloadEvent if successful, None if timeout
        """
        self._wait_event.clear()

        # If not running, start temporarily
        was_running = self._running
        if not was_running:
            self.start()

        try:
            signaled = self._wait_event.wait(timeout)
            return self._last_download if signaled else None
        finally:
            if not was_running:
                self.stop()

    def _scan_files(self) -> set:
        """Scan all watch paths for current files."""
        files = set()
        for path in self._watch_paths:
            if not os.path.exists(path):
                continue
            try:
                for entry in os.scandir(path):
                    if entry.is_file():
                        files.add(entry.path)
            except OSError:
                continue
        return files

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                current_files = self._scan_files()
                now = time.time()

                # Check for new files
                new_files = current_files - self._known_files

                for file_path in new_files:
                    # Ignore temporary download files (.crdownload, .tmp, .part)
                    if self._is_temp_file(file_path):
                        continue

                    # Start tracking
                    self._pending_files[file_path] = {
                        "start_time": now,
                        "last_size": -1,
                        "stable_since": 0,
                    }

                # Update known files
                self._known_files = current_files

                # Check pending files for completion
                completed = []

                for path, info in list(self._pending_files.items()):
                    if not os.path.exists(path):
                        # File deleted/moved during download
                        del self._pending_files[path]
                        continue

                    try:
                        size = os.path.getsize(path)

                        if size == info["last_size"]:
                            if info["stable_since"] == 0:
                                info["stable_since"] = now
                            elif (now - info["stable_since"]) >= self._stability_duration:
                                # Completed!
                                completed.append((path, size, now - info["start_time"]))
                                del self._pending_files[path]
                        else:
                            # Size changed, reset stability
                            info["last_size"] = size
                            info["stable_since"] = 0

                    except OSError:
                        # File locked or inaccessible, just wait
                        continue

                # Notify completions
                for path, size, duration in completed:
                    event = DownloadEvent(
                        path=path,
                        filename=os.path.basename(path),
                        size=size,
                        is_complete=True,
                        duration_sec=duration,
                    )

                    self._last_download = event
                    self._wait_event.set()

                    if self._on_complete:
                        self._on_complete(event)

            except Exception:
                pass  # Keep monitoring

            time.sleep(self._check_interval)

    def _is_temp_file(self, path: str) -> bool:
        """Check if file is a temporary download file."""
        lower = path.lower()
        return (
            lower.endswith(".crdownload")  # Chrome
            or lower.endswith(".tmp")  # Generic
            or lower.endswith(".part")  # Firefox
            or lower.endswith(".download")  # Safari
        )
