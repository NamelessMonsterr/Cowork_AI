
import sys
import subprocess
import os

def run_tests():
    """Run pytest modules sequentially to avoid global collection errors."""
    modules = [
        "tests/unit/",
        "tests/integration/",
        "tests/windows/",
        "tests/test_executor.py",
        "tests/test_voice_pipeline.py",
        "tests/test_hardening.py",
        "tests/test_restricted_shell_policy.py"
    ]
    
    total_failed = 0
    results = []
    
    print(">>> Starting Robust Test Suite Execution...\n")
    
    for module in modules:
        # Check if path exists
        if not os.path.exists(module.strip("/")):
            print(f"⚠️ SKIPPING missing module: {module}")
            continue
            
        print(f"Testing: {module} ...")
        cmd = [sys.executable, "-m", "pytest", module, "-v", "--tb=short"]
        
        try:
            # Run without check=True so we see output even on failure
            # Use encoding='utf-8' but handle potential errors
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            status = "[PASS]" if proc.returncode == 0 else "[FAIL]"
            if proc.returncode != 0:
                total_failed += 1
                
            results.append((module, status, proc.returncode))
            print(f"   Result: {status} (Exit Code: {proc.returncode})")
            
            # Print failure details immediately
            if proc.returncode != 0:
                print("\n   FAILURE DETAILS:")
                lines = proc.stdout.splitlines()[-15:]
                for line in lines:
                    print(f"      {line}")
            print("-" * 50)
            
        except Exception as e:
            print(f"   CRASH: {e}")
            total_failed += 1
    
    print("\nTEST SUMMARY")
    print("=" * 40)
    for mod, stat, code in results:
        print(f"{stat} : {mod}")
    print("=" * 40)
    
    if total_failed == 0:
        print("\nALL MODULES PASSED")
        return 0
    else:
        print(f"\n{total_failed} MODULES FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())
