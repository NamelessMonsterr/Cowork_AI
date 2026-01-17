import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from assistant.computer.windows import WindowsComputer

def test_launcher():
    computer = WindowsComputer()
    # Mock session auth for test
    computer.set_session_verifier(lambda: None)
    
    print("Testing dynamic launcher...")
    
    # Test 1: Notepad (Common)
    print("Launching Notepad...")
    res = computer.launch_app("notepad")
    print(f"Notepad: {res}")
    
    # Test 2: Calc (Common)
    print("Launching Calc...")
    res = computer.launch_app("calc")
    print(f"Calc: {res}")
    
    # Test 3: Explorer (Shell)
    print("Launching Explorer...")
    res = computer.launch_app("explorer")
    print(f"Explorer: {res}")

if __name__ == "__main__":
    test_launcher()
