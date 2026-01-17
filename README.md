# ⚡ Flash Assistant

> **Voice-Controlled Desktop Automation Agent** — The AI that controls your computer.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/react-18+-61DAFB.svg)](https://reactjs.org/)
[![Windows](https://img.shields.io/badge/platform-windows-0078D6.svg)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set OpenAI Key

```bash
# Windows
set OPENAI_API_KEY=sk-your-key

# Or create .env file from example
copy .env.example .env
```

### 3. Start Backend

```bash
python -m uvicorn assistant.main:app --host 127.0.0.1 --port 8765
```

### 4. Start UI

```bash
cd ui
npm install
npm start
```

---

## ✨ Features

| Feature              | Description                           |
| :------------------- | :------------------------------------ |
| **🗣️ Voice Control** | Speak commands, Flash executes them   |
| **🔄 Self-Healing**  | Auto-recovers from popups, UI changes |
| **👁️ Hybrid Vision** | UIA + OCR + Coordinates strategies    |
| **🔌 Plugins**       | Extend with custom tools              |
| **👥 Team Mode**     | Multi-agent task delegation           |
| **☁️ Cloud Sync**    | Settings sync across devices          |
| **🧠 Learning**      | Adapts to your apps over time         |
| **📊 Observability** | Execution timeline with detailed logs |

## E2E Testing 🎭

Flash AI uses [Playwright](https://playwright.dev/) for End-to-End testing.

### Prerequisites

1.  Verify the backend is running (`localhost:8765`)
2.  Verify the UI is running (`localhost:3000` or `3001` - configurable in `playwright.config.ts`)

### Running Tests

```bash
cd ui
# Install browsers (first time)
npx playwright install

# Run all tests
npm run test:e2e

# Run with interactive UI
npm run test:e2e:ui

# Debug mode
npm run test:e2e:debug
```

---

## 📊 Benchmarks

Flash AI includes a rigorous benchmark suite to validate its capabilities across various desktop tasks.

### Running Benchmarks

To run the benchmark suite, set the environment variable `COWORK_BENCHMARK_MODE=1`. This enables the `SystemStrategy` for handling OS-level commands and grants necessary permissions for automated testing.

```bash
# Run the 10-task subset
set COWORK_BENCHMARK_MODE=1
python -m assistant.benchmark.cli --suite 10_tasks.yaml
```

### Status

- **Beta Readiness**: Verified
- **Pass Rate**: 100% on core regression suite (app launching, text input, shell commands).

---

## 📂 Project Structure

```
Flash-Assistant/
├── assistant/           # Backend (Python/FastAPI)
│   ├── agent/           # Planner + LLM
│   ├── executor/        # Strategies + Verification
│   ├── safety/          # SessionAuth, Budget, Guards
│   ├── plugins/         # Plugin system
│   ├── learning/        # Adaptive ranking
│   ├── cloud/           # Sync engine
│   └── config/          # Settings + Paths
├── ui/                  # Frontend (React/Electron)
│   ├── src/
│   │   ├── pages/       # Settings, Permissions, etc.
│   │   └── components/  # UI components
│   └── public/
│       └── electron.js  # Electron main process
├── tests/               # Pytest test suite
└── backend/             # Build scripts
```

---

## 🔒 Security Model

| Layer                   | Protection                                |
| :---------------------- | :---------------------------------------- |
| **SessionAuth**         | 30-min TTL, explicit grant required       |
| **PlanGuard**           | Reviews actions before execution          |
| **Kill Switch**         | `Ctrl+Shift+Escape` stops everything      |
| **Sandboxed Plugins**   | Isolated process with permissions         |
| **Sensitive Detection** | Excludes bank/login windows from learning |

---

## 🛠️ Configuration

Settings are stored in `%APPDATA%/CoworkAI/settings.json`:

```json
{
  "safety": {
    "session_ttl_minutes": 30,
    "enable_kill_switch": true
  },
  "learning": {
    "enabled": true,
    "exclude_sensitive_windows": true
  },
  "cloud": {
    "enabled": false
  },
  "voice": {
    "engine_preference": "auto",
    "record_seconds": 5
  }
}
```

---

## 📦 Building for Distribution

```bash
# Build backend executable
cd backend
python build_backend.py

# Build Electron installer
cd ui
npm run dist
```

Output: `ui/dist/Flash-Assistant-Setup.exe`

---

## 📄 License

MIT © 2026 Flash Assistant
