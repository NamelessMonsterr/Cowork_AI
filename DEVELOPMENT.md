# Cowork AI - Development Setup Guide

## Quick Start (Windows 10/11)

### 1. Install Python Dependencies

```bash
# Install exact pinned versions
pip install -r requirements.txt

# Or use virtual environment (recommended)
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
copy .env.example .env

# Edit .env and set your OpenAI API key
# OPENAI_API_KEY=sk-your-key-here
```

### 3. Start Backend

```bash
# Option 1: Using helper script
python run_backend.py

# Option 2: Direct uvicorn
python -m uvicorn assistant.main:app --host 127.0.0.1 --port 8765 --reload
```

### 4. Start Frontend (separate terminal)

```bash
cd ui
npm install
npm start
```

### 5. Test Voice Integration

The voice system now has three engines:

1. **FasterWhisper** (local, preferred) - requires `faster-whisper` package
2. **OpenAI Whisper API** (fallback) - requires OpenAI API key
3. **Mock STT** (development) - always available

Check STT status:

```bash
curl http://localhost:8765/voice/health
```

Test mic transcription:

```bash
curl -X POST http://localhost:8765/voice/transcribe_mic?duration=5
```

## Voice Integration Fixed

### What Changed

✅ **Voice WebSocket now integrates with STT engine**

- Removed TODO placeholder
- Added actual STT engine integration
- Added `/voice/transcribe_mic` endpoint for direct mic access
- Added `/voice/health` endpoint for STT status

### Using Voice

**From UI**: Click microphone button → Speak → Get transcript

**From API**:

```python
import requests

# Grant session permission first
resp = requests.post("http://localhost:8765/permission/grant")

# Transcribe from microphone
resp = requests.post("http://localhost:8765/voice/transcribe_mic?duration=5")
print(resp.json()["transcript"])
```

## Architecture

```
UI (React) ← → Backend (FastAPI) → STT Engine → Voice Input
                    ↓
               Planner (LLM)
                    ↓
              PlanGuard (Security)
                    ↓
            Executor (Windows Automation)
```

## Development Tips

### Enable Mock STT (for testing without audio hardware)

Edit `assistant/main.py`, find STT initialization:

```python
# Change prefer_mock=False to prefer_mock=True
state.stt = STT(prefer_mock=True)
```

### Check Logs

```bash
# View recent logs
type logs\*.log

# Watch live
Get-Content logs\app.log -Wait -Tail 50
```

### Run Tests

```bash
# Backend tests
pytest tests/

# UI tests
cd ui
npm run test:e2e
```

## Troubleshooting

### Voice not working?

1. Check STT health: `curl http://localhost:8765/voice/health`
2. If FasterWhisper fails, install audio dependencies: `pip install sounddevice`
3. Falls back to OpenAI Whisper (needs API key)
4. Falls back to Mock STT (always works, returns test phrases)

### Backend won't start?

1. Check Python version: `python --version` (need 3.11+)
2. Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
3. Check port 8765 not in use: `netstat -ano | findstr :8765`

### UI won't connect?

1. Verify backend is running on `http://localhost:8765`
2. Check CORS settings in `assistant/main.py`
3. Clear browser cache and retry

## Production Deployment

See `README.md` for building distributable installers:

```bash
# Build backend executable
cd backend
python build_backend.py

# Build Electron app
cd ui
npm run dist
```

## Next Steps

- [ ] Complete WebSocket audio streaming (currently uses mic endpoint)
- [ ] Add audio chunk aggregation for real-time streaming
- [ ] Implement voice activity detection (VAD)
- [ ] Add noise cancellation
- [ ] Support multiple audio codecs

## Resources

- **Main README**: Full feature documentation
- **API Docs**: Start backend and visit `http://localhost:8765/docs`
- **STT Module**: `assistant/voice/stt.py` - Engine implementations
- **Voice API**: `assistant/api/voice.py` - WebSocket and HTTP endpoints
