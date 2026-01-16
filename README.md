# ⚡ Flash AI Assistant

> **The High-Performance, Voice-Controlled Desktop Agent**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18.0+-61DAFB.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)

Flash is a next-generation desktop assistant that combines **local speed** with **cloud intelligence**. It sees your screen, hears your voice, and executes complex tasks instantly.

---

## ✨ Capabilities

| Feature                  | Description                                                     | Speed              |
| :----------------------- | :-------------------------------------------------------------- | :----------------- |
| **⚡ Fast Actions**      | Open apps, take screenshots, lock screen, control media.        | **<100ms** (Local) |
| **🧠 Deep Intelligence** | "Summarize this window", "Write a poem", "Analyze this error".  | Smart (GPT-4o)     |
| **👁️ Computer Vision**   | Analyzes screen context to understand what you're looking at.   | Integrated         |
| **🗣️ Voice I/O**         | Full-duplex conversation. Speaks back to you with frontend TTS. | Real-time          |
| **💻 System Control**    | Execute ANY PowerShell command ("Create folder", "Check IP").   | Power User         |

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- Node.js 16+
- OpenAI API Key (Set in `assistant/agent/llm.py` or Environment)

### 2. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the Brain (Backend)
python -m uvicorn assistant.main:app --port 8765
```

### 3. Frontend Setup

```bash
# Open a new terminal
cd ui

# Install Node dependencies
npm install

# Build and Run
npm start
```

---

## 🎮 Usage Guide

**Click the Glowing Core** to activate.

### Voice Commands

- **"Open Notepad"** -> Launches Notepad instantly.
- **"Take a screenshot"** -> Captures screen to `screenshots/`.
- **"Play music"** -> Toggles Spotify/YouTube playback.
- **"Hello"** -> Greets you back.

### Complex Requests

- **"Open Notepad and type a story about space."**
- **"Create a folder named 'Top Secret' on the Desktop."**
- **"What does the text on my screen say?"**

---

## 🛠️ Configuration

| Component         | File                         | Description                              |
| :---------------- | :--------------------------- | :--------------------------------------- |
| **Local Actions** | `assistant/agent/actions.py` | Add new fast Regex commands here.        |
| **LLM Logic**     | `assistant/agent/llm.py`     | Configure GPT models and Fallback logic. |
| **UI Theme**      | `ui/src/App.css`             | Customize the futuristic interface.      |

---

## 4. Recommendations & Future Work

### ⚠️ Technical Debt

- **Clicking Accuracy:** The `click` action is primitive (placeholder). To make "Click the Send button" work, we need coordinate mapping (using an accessibility API or vision model like YOLO/UI-Ref).
- **STT Latency:** Currently using `listen_and_transcribe` which records for fixed blocks. A streaming STT (WebSockets for audio) would feel much snappier.
- **Security:** The `run_command` capability is unrestricted. In a production shared environment, this would need a sandbox or user confirmation prompt for high-risk commands.

---

## 📄 License

MIT © 2024 Flash AI Project
