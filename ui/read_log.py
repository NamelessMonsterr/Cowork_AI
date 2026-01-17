try:
    with open('test_t1_fix.txt', 'r', encoding='utf-8', errors='replace') as f:
        print("--- LOG START ---")
        lines = f.readlines()
        for line in lines:
            if "failed" in line or "passed" in line or "skipped" in line or "Error:" in line or "Running" in line:
                print(line.strip())
except Exception as e:
    print(f"Error: {e}")
