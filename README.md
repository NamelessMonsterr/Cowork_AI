# VoiceCommander 🎙️

Control your computer with voice commands. Open apps, type text, take screenshots - hands free.

![Demo](demo.gif)

## ⚡ Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Server

```bash
python run_backend.py
```

### 3. Open the UI

Double-click `demo.html` in your file explorer (or open in any browser).

Click the microphone button and say **"Open notepad"**!

## 🎮 Voice Commands

| Say...           | Result                                            |
| ---------------- | ------------------------------------------------- |
| "Open [app]"     | Launches apps (notepad, calculator, chrome, etc.) |
| "Type [text]"    | Types text at your current cursor position        |
| "Screenshot"     | Saves a screenshot to your `screenshots/` folder  |
| "Press [key]"    | Simulates a keypress (e.g., "press enter")        |
| "Wait [seconds]" | Pauses execution for X seconds                    |
| "Minimize"       | Minimizes current window                          |
| "Volume up/down" | Adjusts system volume                             |

## ⚠️ Demo Mode

This is a **working prototype** with safety bypasses enabled for demonstration purposes.

- It auto-grants session permissions.
- It executes commands immediately via the `/just_do_it` endpoint.
- **Use at your own risk.**

## 🛣️ Roadmap

- [ ] Proper authentication (JWT)
- [ ] Wake word detection ("Hey Computer")
- [ ] macOS/Linux support
- [ ] Plugin system
- [ ] Commercial license

## 📄 License

MIT - Use at your own risk.

Built with **FastAPI**, **Whisper** (locally), and **Python**.
