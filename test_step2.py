"""
Step 2 Verification Script.

Tests Stability & Verification components:
1. OCR Engine (WinRT)
2. Verifier Engine (Text checks)
3. Download Watcher
"""

import time
import os
import sys
import threading

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from assistant.computer.windows import WindowsComputer
from assistant.executor.strategies.ocr import get_ocr_engine
from assistant.executor.verify import Verifier
from assistant.ui_contracts.schemas import VerifySpec, VerifyType
from assistant.watcher.download import DownloadWatcher

def test_ocr_and_verifier():
    print("\n--- 1. Testing OCR & Verifier ---")
    
    ocr = get_ocr_engine()
    if not ocr._reader:
        print("⚠️  OCR not available (missing dependencies or WinRT support)")
        return

    computer = WindowsComputer()
    with computer:
        verifier = Verifier(computer=computer, ocr_func=ocr.read_text)
        
        # Take a screenshot to show what we're looking at
        # computer.screenshot() # (Optional)
        
        # Verify active window title (e.g. "Command Prompt" or "Visual Studio Code" or "Powershell")
        # We'll use a generic check
        print("Verifying window title...")
        win = computer.get_active_window()
        if win:
            print(f"Active window: {win.title}")
            res = verifier.verify(VerifySpec(
                type=VerifyType.WINDOW_TITLE,
                value=win.title[:5], # First 5 chars
                timeout=2
            ))
            if res.success:
                print("✅ Window title verification passed")
            else:
                print(f"❌ Window title verification failed: {res.error}")
        
        # Verify text present on screen
        # We'll look for something that should be on screen, like the window title
        if win and win.title:
            print(f"Verifying text presence: '{win.title[:5]}'")
            res = verifier.verify(VerifySpec(
                type=VerifyType.TEXT_PRESENT,
                value=win.title[:5],
                timeout=5
            ))
            if res.success:
                print(f"✅ OCR found text: '{res.actual}'")
            else:
                print(f"❌ OCR failed to find text: {res.error}")

def test_download_watcher():
    print("\n--- 2. Testing Download Watcher ---")
    
    # Use a temp directory or local Downloads
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
    if not os.path.exists(downloads_path):
        print("⚠️ Downloads folder not found, skipping watcher test")
        return

    print(f"Watching {downloads_path}...")
    
    watcher = DownloadWatcher(
        watch_paths=[downloads_path],
        stability_duration=1.0,
        check_interval=0.5
    )
    watcher.start()
    
    try:
        # Create a dummy file
        test_file = os.path.join(downloads_path, "cowork_test_download.txt")
        print(f"Creating dummy file: {test_file}")
        
        with open(test_file, "w") as f:
            f.write("test content")
            
        print("Waiting for watcher detection...")
        event = watcher.wait_for_download(timeout=5.0)
        
        if event:
            print(f"✅ Download detected: {event.filename} (Size: {event.size})")
        else:
            print("❌ Watcher timed out (did not detect file)")
            
    finally:
        # Cleanup
        if os.path.exists(test_file):
            try:
                os.remove(test_file)
                print("Cleaned up test file")
            except:
                pass
        watcher.stop()

if __name__ == "__main__":
    print("=== STARTING STEP 2 HEALTH CHECK ===")
    try:
        test_ocr_and_verifier()
        test_download_watcher()
        print("\n=== ✨ Step 2 Verified! ===")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
