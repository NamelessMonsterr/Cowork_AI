try:
    with open('mock_status.txt', 'r', encoding='utf-16-le', errors='replace') as f:
        print(f.read())
except Exception as e:
    # Try utf-8 just in case
    try:
        with open('mock_status.txt', 'r', encoding='utf-8', errors='replace') as f:
            print(f.read())
    except Exception as e2:
        print(f"Error: {e}, {e2}")
