"""
Demo/Verification for Windows Modules W1 & W2.
Run this to verify Capture and Input integration.
"""
import time
import os
import sys

# Ensure assistant module is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from assistant.computer.windows import WindowsComputer

def main():
    print(">>> Initializing WindowsComputer...")
    try:
        comp = WindowsComputer()
        print("✅ Initialization successful.")
    except Exception as e:
        print(f"❌ Init failed: {e}")
        return

    # W1: Capture
    print("\n>>> Testing Screen Capture (W1)...")
    path = comp.take_screenshot()
    if path and os.path.exists(path):
        print(f"✅ Screenshot saved: {path}")
    else:
        print("❌ Screenshot failed.")

    # W2: Input
    print("\n>>> Testing Input (W2)...")
    print("Launching Notepad...")
    if comp.launch_app("notepad"):
        print("✅ Notepad launched (command sent). Waiting for Window...")
        time.sleep(2) # Wait for load using simple sleep (heuristic)
        
        print("Typing text...")
        comp.type_text("Hello from Phase W2 Automation! 🚀", interval=0.05)
        print("✅ Text typed.")
        
        print("\n>>> Demo Complete.")
    else:
        print("❌ Launch failed.")

if __name__ == "__main__":
    main()
