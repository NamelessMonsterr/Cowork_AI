import os
import sys
import multiprocessing
import uvicorn

# Necessary for PyInstaller when using multiprocessing (e.g. in Uvicorn workers or plugins)
multiprocessing.freeze_support()

# Add current directory to path so we can import 'assistant'
if getattr(sys, 'frozen', False):
    # Running in a bundle
    base_dir = sys._MEIPASS
else:
    # Running in normal python
    base_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, base_dir)

if __name__ == "__main__":
    try:
        # Import app here to avoid side effects at module level
        from assistant.main import app
        from assistant.config.settings import get_settings
        
        # Get port from env (set by Electron) or fallback to settings
        settings = get_settings()
        port = int(os.environ.get("PORT", settings.server.port))
        
        print(f"Starting Flash AI Backend on port {port}...")
        
        # Run server
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
        
    except Exception as e:
        print(f"Backend failed to start: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
