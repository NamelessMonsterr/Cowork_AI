try:
    with open('test_debug.txt', 'r', encoding='utf-16') as f:
        print(f.read())
except Exception as e:
    try:
        with open('test_debug.txt', 'r', encoding='utf-8', errors='ignore') as f:
            print(f.read())
    except Exception as e2:
        print(f"Failed to read: {e}, {e2}")
