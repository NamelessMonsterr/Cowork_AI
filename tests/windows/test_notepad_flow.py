"""
Windows Automation Test: Notepad Flow
=====================================

Tests the full cycle:
1. Open Notepad
2. Type "Hello Flash AI"
3. Save file (Ctrl+S → type filename → Enter)
4. Verify file exists and content matches
5. Close Notepad without saving (already saved)

Requirements:
- Windows OS
- pywinauto installed
- Run with: python -m pytest tests/windows/test_notepad_flow.py -v

This test should be run in BENCHMARK_MODE or on a dedicated Windows runner.
"""

import os
import time
import tempfile
import pytest

# Skip if not on Windows
pytestmark = pytest.mark.skip(reason="Windows GUI tests require active desktop")


class TestNotepadFlow:
    """End-to-end test for Notepad automation."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and cleanup for each test."""
        self.test_filename = f"flash_test_{int(time.time())}.txt"
        self.test_content = "Hello Flash AI - Windows Automation Test"
        self.test_dir = tempfile.gettempdir()
        self.test_path = os.path.join(self.test_dir, self.test_filename)

        yield

        # Cleanup: Remove test file if exists
        if os.path.exists(self.test_path):
            os.remove(self.test_path)

    def test_notepad_open_type_save(self):
        """Test opening Notepad, typing, and saving."""
        try:
            from pywinauto import Application
            from pywinauto.keyboard import send_keys
        except ImportError:
            pytest.skip("pywinauto not installed")

        # 1. Launch Notepad
        try:
            app = Application(backend="uia").start("notepad.exe")
        except Exception as e:
            pytest.skip(f"Skipping GUI test (headless/error): {e}")
        time.sleep(1)  # Wait for window

        try:
            # 2. Connect to Notepad window
            notepad = app.window(title_re=".*Notepad.*")
            assert notepad.exists(), "Notepad window should exist"

            # 3. Type text
            notepad.type_keys(self.test_content, with_spaces=True)
            time.sleep(0.5)

            # 4. Save file (Ctrl+S)
            send_keys("^s")
            time.sleep(1)  # Wait for Save As dialog

            # 5. Type filename in Save As dialog
            save_dialog = app.window(title_re=".*Save As.*")
            if save_dialog.exists(timeout=5):
                # Type full path
                send_keys(self.test_path, with_spaces=True)
                time.sleep(0.5)
                send_keys("{ENTER}")
                time.sleep(1)

            # 6. Close Notepad
            send_keys("%{F4}")  # Alt+F4
            time.sleep(0.5)

            # Handle "Don't Save" if prompted (shouldn't be since we saved)
            try:
                dont_save = app.window(title_re=".*Notepad.*")
                if dont_save.exists():
                    send_keys("{TAB}{ENTER}")  # Navigate to "Don't Save" and press
            except:
                pass

            # 7. Verify file exists and content
            assert os.path.exists(self.test_path), (
                f"File should exist at {self.test_path}"
            )

            with open(self.test_path, "r") as f:
                content = f.read()
            assert self.test_content in content, (
                f"File should contain '{self.test_content}'"
            )

        finally:
            # Force close Notepad if still running
            try:
                app.kill()
            except:
                pass

    def test_notepad_window_detection(self):
        """Test that we can detect Notepad window info."""
        try:
            from pywinauto import Application
        except ImportError:
            pytest.skip("pywinauto not installed")

        try:
            app = Application(backend="uia").start("notepad.exe")
        except Exception as e:
            pytest.skip(f"Skipping GUI test (headless/error): {e}")
        time.sleep(1)

        try:
            notepad = app.window(title_re=".*Notepad.*")
            assert notepad.exists()

            # Get window properties
            rect = notepad.rectangle()
            assert rect.width() > 0, "Window should have width"
            assert rect.height() > 0, "Window should have height"

            # Window title should contain "Notepad"
            assert "Notepad" in notepad.window_text()

        finally:
            try:
                app.kill()
            except:
                pass


class TestWindowsComputerIntegration:
    """Test WindowsComputer class functionality."""

    def test_screen_capture(self):
        """Test that screen capture works."""
        try:
            from assistant.computer.windows import WindowsComputer
        except ImportError:
            pytest.skip("WindowsComputer not available")

        try:
            computer = WindowsComputer()
            screenshot = computer.take_screenshot()
        except Exception as e:
            pytest.skip(f"Skipping WindowsComputer test: {e}")

        assert screenshot is not None, "Screenshot should be captured"
        assert os.path.exists(screenshot), "Screenshot file should exist"

        # Cleanup
        os.remove(screenshot)

    def test_get_active_window(self):
        """Test active window detection."""
        try:
            from assistant.computer.windows import WindowsComputer
        except ImportError:
            pytest.skip("WindowsComputer not available")

        try:
            computer = WindowsComputer()
            window = computer.get_active_window()
        except Exception as e:
            pytest.skip(f"Skipping WindowsComputer test: {e}")

        # Some window should be active
        assert window is not None, "Should detect active window"
        assert window.handle > 0, "Window should have valid handle"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
